import cv2
import numpy as np
from typing import Tuple, Optional, Union

class FaceAligner:
    """
    EXACT implementation of DeepFace-style alignment logic.
    No behavior changes. No math changes.
    """
    
    def __init__(self):
        pass

    def __extract_sub_image(
        self,
        img: np.ndarray,
        facial_area: Tuple[int, int, int, int],
    ) -> Tuple[np.ndarray, int, int]:
        """
        Get the sub image with given facial area while expanding the facial region
            to ensure alignment does not shift the face outside the image.

        This function doubles the height and width of the face region,
        and adds black pixels if necessary.

        Args:
            - img (np.ndarray): pre-loaded image with detected face
            - facial_area (tuple of int): Representing the (x, y, w, h) of the facial area.

        Returns:
            - extracted_face (np.ndarray): expanded facial image
            - relative_x (int): adjusted x-coordinates relative to the expanded region
            - relative_y (int): adjusted y-coordinates relative to the expanded region
        """
        x, y, w, h = facial_area
        relative_x = int(0.5 * w)
        relative_y = int(0.5 * h)

        # calculate expanded coordinates
        x1, y1 = x - relative_x, y - relative_y
        x2, y2 = x + w + relative_x, y + h + relative_y

        # most of the time, the expanded region fits inside the image
        if x1 >= 0 and y1 >= 0 and x2 <= img.shape[1] and y2 <= img.shape[0]:
            return img[y1:y2, x1:x2], relative_x, relative_y

        # but sometimes, we need to add black pixels
        # ensure the coordinates are within bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)
        cropped_region = img[y1:y2, x1:x2]

        # create a black image
        extracted_face = np.zeros(
            (h + 2 * relative_y, w + 2 * relative_x, img.shape[2]),
            dtype=img.dtype,
        )

        # map the cropped region
        start_x = max(0, relative_x - x)
        start_y = max(0, relative_y - y)

        extracted_face[
            start_y : start_y + cropped_region.shape[0],
            start_x : start_x + cropped_region.shape[1],
        ] = cropped_region

        return extracted_face, relative_x, relative_y


    def __align_img_wrt_eyes(
        self,
        img: np.ndarray,
        left_eye: Optional[Union[list, tuple]],
        right_eye: Optional[Union[list, tuple]],
    ) -> Tuple[np.ndarray, float]:
        """
        Align a given image horizantally with respect to their left and right eye locations
        Args:
            img (np.ndarray): pre-loaded image with detected face
            left_eye (list or tuple): coordinates of left eye with respect to the person itself
            right_eye(list or tuple): coordinates of right eye with respect to the person itself
        Returns:
            img (np.ndarray): aligned facial image
        """
        # if eye could not be detected for the given image, return image itself
        if left_eye is None or right_eye is None:
            return img, 0

        # sometimes unexpectedly detected images come with nil dimensions
        if img.shape[0] == 0 or img.shape[1] == 0:
            return img, 0

        angle = float(
            np.degrees(
                np.arctan2(
                    left_eye[1] - right_eye[1],
                    left_eye[0] - right_eye[0],
                )
            )
        )

        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        img = cv2.warpAffine(
            img,
            M,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        )

        return img, angle


    def __project_facial_area(
        self,
        facial_area: Tuple[int, int, int, int],
        angle: float,
        size: Tuple[int, int],
    ) -> Tuple[int, int, int, int]:
        """
        Update pre-calculated facial area coordinates after image itself
            rotated with respect to the eyes.
        Inspried from the work of @UmutDeniz26 - github.com/serengil/retinaface/pull/80

        Args:
            facial_area (tuple of int): Representing the (x1, y1, x2, y2) of the facial area.
                x2 is equal to x1 + w1, and y2 is equal to y1 + h1
            angle (float): Angle of rotation in degrees. Its sign determines the direction of rotation.
                        Note that angles > 360 degrees are normalized to the range [0, 360).
            size (tuple of int): Tuple representing the size of the image (width, height).

        Returns:
            rotated_coordinates (tuple of int): Representing the new coordinates
                (x1, y1, x2, y2) or (x1, y1, x1+w1, y1+h1) of the rotated facial area.
        """

        # Normalize the witdh of the angle so we don't have to
        # worry about rotations greater than 360 degrees.
        # We workaround the quirky behavior of the modulo operator
        # for negative angle values.
        direction = 1 if angle >= 0 else -1
        angle = abs(angle) % 360
        if angle == 0:
            return facial_area

        # Angle in radians
        angle = angle * np.pi / 180
        
        height, width = size

        # Translate the facial area to the center of the image
        x = (facial_area[0] + facial_area[2]) / 2 - width / 2
        y = (facial_area[1] + facial_area[3]) / 2 - height / 2

        # Rotate the facial area
        x_new = x * np.cos(angle) + y * direction * np.sin(angle)
        y_new = -x * direction * np.sin(angle) + y * np.cos(angle)

        # Translate the facial area back to the original position
        x_new = x_new + width / 2
        y_new = y_new + height / 2

        # Calculate projected coordinates after alignment
        x1 = x_new - (facial_area[2] - facial_area[0]) / 2
        y1 = y_new - (facial_area[3] - facial_area[1]) / 2
        x2 = x_new + (facial_area[2] - facial_area[0]) / 2
        y2 = y_new + (facial_area[3] - facial_area[1]) / 2

        # validate projected coordinates are in image's boundaries
        x1 = max(int(x1), 0)
        y1 = max(int(y1), 0)
        x2 = min(int(x2), width)
        y2 = min(int(y2), height)

        return x1, y1, x2, y2


    def align_face(
        self,
        img: np.ndarray,
        facial_area: Tuple[int, int, int, int],
        left_eye: Optional[Tuple[int, int]],
        right_eye: Optional[Tuple[int, int]],
    ) -> np.ndarray:
        
        if left_eye is None or right_eye is None:
            raise ValueError("Cannot align face: left or right eye missing")
        
        x, y, w, h = facial_area
        sub_img, relative_x, relative_y = self.__extract_sub_image(img=img, facial_area=(x, y, w, h))

        aligned_sub_img, angle = self.__align_img_wrt_eyes(
            img=sub_img, left_eye=left_eye, right_eye=right_eye
        )
        
        # add a little bit margin to bbox so the align face bbox is a little bit losser 
        margin = 0.1  # 10–25% is typical
        
        w_margin = int(w * (1 + margin))
        h_margin = int(h * (1 + margin))
        dx = (w_margin - w) // 2
        dy = (h_margin - h) // 2

        rx1, ry1, rx2, ry2 = self.__project_facial_area(
            facial_area=(
                relative_x - dx,
                relative_y - dy,
                relative_x + w + dx,
                relative_y + h + dy,
            ),
            angle=angle,
            size=(sub_img.shape[0], sub_img.shape[1]),
        )
        
        detected_face = aligned_sub_img[
            int(ry1) : int(ry2), int(rx1) : int(rx2)
        ]
        
        if detected_face is None or detected_face.size == 0:
            raise ValueError("Aligned face is empty after processing")

        return cv2.rotate(detected_face, cv2.ROTATE_180)