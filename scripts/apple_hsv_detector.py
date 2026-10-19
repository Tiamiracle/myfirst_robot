#!/usr/bin/env python3
"""Detect red simulated apples with HSV and publish 3D ROS 2 poses."""

import math

import cv2
import message_filters
import numpy as np
import rclpy
from cv_bridge import CvBridge, CvBridgeError
from geometry_msgs.msg import PointStamped, Pose, PoseArray
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import Header
from tf2_geometry_msgs import do_transform_point
from tf2_ros import Buffer, TransformException, TransformListener
from visualization_msgs.msg import Marker, MarkerArray


class AppleHsvDetector(Node):
    """Segment red apples in RGB-D images and locate them in base_link."""

    def __init__(self):
        super().__init__("apple_hsv_detector")
        self._declare_parameters()
        self._bridge = CvBridge()
        self._camera_info = None
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

        self._poses_pub = self.create_publisher(PoseArray, "~/poses", 10)
        self._markers_pub = self.create_publisher(MarkerArray, "~/markers", 10)
        self._debug_pub = self.create_publisher(Image, "~/debug_image", 10)
        self._mask_pub = self.create_publisher(Image, "~/mask", 10)

        self.create_subscription(
            CameraInfo,
            self.get_parameter("camera_info_topic").value,
            self._camera_info_callback,
            qos_profile_sensor_data,
        )
        self._rgb_sub = message_filters.Subscriber(
            self,
            Image,
            self.get_parameter("rgb_topic").value,
            qos_profile=qos_profile_sensor_data,
        )
        self._depth_sub = message_filters.Subscriber(
            self,
            Image,
            self.get_parameter("depth_topic").value,
            qos_profile=qos_profile_sensor_data,
        )
        self._sync = message_filters.ApproximateTimeSynchronizer(
            [self._rgb_sub, self._depth_sub],
            queue_size=self.get_parameter("sync_queue_size").value,
            slop=self.get_parameter("sync_slop").value,
        )
        self._sync.registerCallback(self._image_callback)
        self.get_logger().info("Apple HSV detector is ready")

    def _declare_parameters(self):
        self.declare_parameter("rgb_topic", "/camera/color/image_raw")
        self.declare_parameter("depth_topic", "/camera/depth/image_raw")
        self.declare_parameter("camera_info_topic", "/camera/color/camera_info")
        self.declare_parameter("target_frame", "base_link")
        self.declare_parameter("source_frame", "camera_optical_frame")
        self.declare_parameter("sync_queue_size", 10)
        self.declare_parameter("sync_slop", 0.10)
        self.declare_parameter("red_low_hue_max", 10)
        self.declare_parameter("red_high_hue_min", 170)
        self.declare_parameter("saturation_min", 80)
        self.declare_parameter("value_min", 50)
        self.declare_parameter("open_kernel_size", 3)
        self.declare_parameter("close_kernel_size", 5)
        self.declare_parameter("min_contour_area", 100.0)
        self.declare_parameter("min_circularity", 0.55)
        self.declare_parameter("min_aspect_ratio", 0.65)
        self.declare_parameter("max_aspect_ratio", 1.50)
        self.declare_parameter("center_exclusion_width", 24)
        self.declare_parameter("depth_window_radius", 4)
        self.declare_parameter("depth_scale", 1.0)
        self.declare_parameter("depth_min", 0.10)
        self.declare_parameter("depth_max", 8.0)

    def _camera_info_callback(self, message):
        if message.k[0] > 0.0 and message.k[4] > 0.0:
            self._camera_info = message

    def _image_callback(self, rgb_message, depth_message):
        try:
            bgr = self._bridge.imgmsg_to_cv2(rgb_message, desired_encoding="bgr8")
            depth = self._bridge.imgmsg_to_cv2(depth_message, desired_encoding="passthrough")
        except CvBridgeError as error:
            self.get_logger().error("Image conversion failed: %s" % error)
            return

        if depth.ndim != 2:
            self.get_logger().warn("Depth image is not single-channel; frame skipped")
            return

        mask = self._red_mask(bgr)
        candidates = self._find_candidates(mask)
        debug = bgr.copy()
        poses = PoseArray()
        poses.header = Header(stamp=rgb_message.header.stamp,
                              frame_id=self.get_parameter("target_frame").value)
        markers = MarkerArray()
        markers.markers.append(self._delete_all_marker(rgb_message.header.stamp))

        for index, candidate in enumerate(candidates):
            contour, x, y, width, height, circularity = candidate
            cv2.drawContours(debug, [contour], -1, (0, 255, 255), 2)
            cv2.circle(debug, (x, y), 3, (255, 0, 0), -1)
            position = self._position_from_depth(
                x, y, depth, rgb_message.header.stamp
            )
            if position is None:
                cv2.putText(debug, "invalid depth", (x, max(15, y - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
                continue

            pose = Pose()
            pose.position = position
            pose.orientation.w = 1.0
            poses.poses.append(pose)
            markers.markers.extend(
                self._markers(index, position, rgb_message.header.stamp, circularity)
            )
            distance = math.sqrt(
                position.x * position.x
                + position.y * position.y
                + position.z * position.z
            )
            label = "%d: %.2fm" % (index + 1, distance)
            cv2.putText(debug, label, (x, max(15, y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        self._poses_pub.publish(poses)
        self._markers_pub.publish(markers)
        self._publish_debug(rgb_message.header, debug, mask)

    def _red_mask(self, bgr):
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        saturation_min = self.get_parameter("saturation_min").value
        value_min = self.get_parameter("value_min").value
        low_red = cv2.inRange(
            hsv, np.array([0, saturation_min, value_min]),
            np.array([self.get_parameter("red_low_hue_max").value, 255, 255])
        )
        high_red = cv2.inRange(
            hsv,
            np.array([self.get_parameter("red_high_hue_min").value,
                      saturation_min, value_min]),
            np.array([180, 255, 255]),
        )
        mask = cv2.bitwise_or(low_red, high_red)
        open_kernel = self._kernel("open_kernel_size")
        close_kernel = self._kernel("close_kernel_size")
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel)
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel)

    def _kernel(self, parameter):
        size = max(1, int(self.get_parameter(parameter).value))
        if size % 2 == 0:
            size += 1
        return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))

    def _find_candidates(self, mask):
        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        candidates = []
        image_width = mask.shape[1]
        exclusion_half = self.get_parameter("center_exclusion_width").value / 2.0
        exclusion_left = image_width / 2.0 - exclusion_half
        exclusion_right = image_width / 2.0 + exclusion_half
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.get_parameter("min_contour_area").value:
                continue
            perimeter = cv2.arcLength(contour, True)
            if perimeter <= 0.0:
                continue
            circularity = 4.0 * math.pi * area / (perimeter * perimeter)
            if circularity < self.get_parameter("min_circularity").value:
                continue
            left, top, width, height = cv2.boundingRect(contour)
            aspect_ratio = float(width) / float(height)
            if not (self.get_parameter("min_aspect_ratio").value <= aspect_ratio
                    <= self.get_parameter("max_aspect_ratio").value):
                continue
            if left < exclusion_right and left + width > exclusion_left:
                continue
            moments = cv2.moments(contour)
            if moments["m00"] == 0.0:
                continue
            x = int(moments["m10"] / moments["m00"])
            y = int(moments["m01"] / moments["m00"])
            candidates.append((contour, x, y, width, height, circularity))
        return candidates

    def _position_from_depth(self, x, y, depth, stamp):
        if self._camera_info is None:
            self.get_logger().warn("CameraInfo unavailable; no 3D pose published")
            return None
        radius = self.get_parameter("depth_window_radius").value
        x0, x1 = max(0, x - radius), min(depth.shape[1], x + radius + 1)
        y0, y1 = max(0, y - radius), min(depth.shape[0], y + radius + 1)
        samples = depth[y0:y1, x0:x1].astype(np.float64).reshape(-1)
        samples *= self.get_parameter("depth_scale").value
        depth_min = self.get_parameter("depth_min").value
        depth_max = self.get_parameter("depth_max").value
        samples = samples[np.isfinite(samples)]
        samples = samples[(samples >= depth_min) & (samples <= depth_max)]
        if samples.size == 0:
            return None
        z = float(np.median(samples))
        fx, fy = self._camera_info.k[0], self._camera_info.k[4]
        cx, cy = self._camera_info.k[2], self._camera_info.k[5]
        point = PointStamped()
        point.header.stamp = stamp
        point.header.frame_id = self.get_parameter("source_frame").value
        point.point.x = (x - cx) * z / fx
        point.point.y = (y - cy) * z / fy
        point.point.z = z
        try:
            transform = self._tf_buffer.lookup_transform(
                self.get_parameter("target_frame").value,
                point.header.frame_id,
                Time.from_msg(stamp),
                timeout=Duration(seconds=0.1),
            )
            return do_transform_point(point, transform).point
        except TransformException as error:
            self.get_logger().warn("TF unavailable: %s" % error)
            return None

    def _delete_all_marker(self, stamp):
        marker = Marker()
        marker.header = Header(stamp=stamp,
                               frame_id=self.get_parameter("target_frame").value)
        marker.action = Marker.DELETEALL
        return marker

    def _markers(self, index, position, stamp, circularity):
        header = Header(stamp=stamp,
                        frame_id=self.get_parameter("target_frame").value)
        sphere = Marker()
        sphere.header = header
        sphere.ns = "apple_positions"
        sphere.id = index * 2
        sphere.type = Marker.SPHERE
        sphere.action = Marker.ADD
        sphere.pose.position = position
        sphere.pose.orientation.w = 1.0
        sphere.scale.x = sphere.scale.y = sphere.scale.z = 0.08
        sphere.color.r, sphere.color.g, sphere.color.b, sphere.color.a = 1.0, 0.0, 0.0, 1.0
        text = Marker()
        text.header = header
        text.ns = "apple_labels"
        text.id = index * 2 + 1
        text.type = Marker.TEXT_VIEW_FACING
        text.action = Marker.ADD
        text.pose.position = position
        text.pose.position.z += 0.10
        text.pose.orientation.w = 1.0
        text.scale.z = 0.06
        text.color.r, text.color.g, text.color.b, text.color.a = 1.0, 1.0, 1.0, 1.0
        text.text = "apple %d (round %.2f)" % (index + 1, circularity)
        return [sphere, text]

    def _publish_debug(self, header, debug, mask):
        debug_message = self._bridge.cv2_to_imgmsg(debug, encoding="bgr8")
        debug_message.header = header
        mask_message = self._bridge.cv2_to_imgmsg(mask, encoding="mono8")
        mask_message.header = header
        self._debug_pub.publish(debug_message)
        self._mask_pub.publish(mask_message)


def main():
    rclpy.init()
    node = AppleHsvDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
