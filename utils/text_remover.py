import cv2
import os
import numpy as np
import logging
from ocr_processor import OCRProcessor

class TextRemover:
    def __init__(self, inpaint_radius=3, method=cv2.INPAINT_TELEA, log_level=logging.INFO):
        """
        Initialize the TextRemover.

        Args:
            inpaint_radius (int): Radius of a circular neighborhood of each point inpainting is considered.
            method (int): Inpainting method (cv2.INPAINT_TELEA or cv2.INPAINT_NS).
            log_level (int): Logging level.
        """
        self.inpaint_radius = inpaint_radius
        self.method = method
        logging.basicConfig(level=log_level)
        self.logger = logging.getLogger(__name__)

    def remove_text(self, image_path, grouped_boxes, dilation_iter=2):
        """
        Removes text from the image using the provided bounding boxes.

        Args:
            image_path (str): Path to the original image.
            grouped_boxes (list): List of groups, where each group is a list of boxes.
                                  Each box is a list/array of coordinates [[x1, y1], ...].
            dilation_iter (int): Number of iterations for mask dilation to ensure full coverage.

        Returns:
            numpy.ndarray: The image with text removed (inpainted).
        """
        self.logger.info(f"Removing text from: {image_path}")
        
        # 1. Read the image
        img = cv2.imread(image_path)
        if img is None:
            self.logger.error(f"Could not read image: {image_path}")
            return None

        # 2. Create a mask initialized to black
        mask = np.zeros(img.shape[:2], dtype=np.uint8)

        # 3. Draw text boxes on the mask
        count = 0
        for group in grouped_boxes:
            for box in group:
                # box can be a numpy array or a list of lists
                points = np.array(box, dtype=np.int32)
                cv2.fillPoly(mask, [points], 255)
                count += 1
        
        self.logger.info(f"Created mask for {count} text boxes.")

        # 4. Dilate the mask to cover edges and artifacts
        if dilation_iter > 0:
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=dilation_iter)

        # 5. Perform inpainting
        try:
            inpainted_img = cv2.inpaint(img, mask, self.inpaint_radius, self.method)
            self.logger.info("Inpainting completed successfully.")
            return inpainted_img
        except Exception as e:
            self.logger.error(f"Error during inpainting: {e}")
            return None

if __name__ == "__main__":
    # Setup paths
    image_path = "./output_scraper/potential villain.jpg"
    output_path = "./output_text_remover/test_text_remover_result.jpg"
    
    if not os.path.exists(image_path):
        print(f"Error: Test image not found at {image_path}")
        exit()

    # 1. Run OCR
    print("Running OCR...")
    processor = OCRProcessor(use_angle_cls=True, lang='en') # Adjust lang if needed
    grouped_boxes, grouped_texts = processor.perform_ocr(image_path)
    print(f"Found {len(grouped_boxes)} groups of text.")

    # 2. Run Inpainting
    print("Running TextRemover...")
    remover = TextRemover()
    result_image = remover.remove_text(image_path, grouped_boxes)

    # 3. Save result
    if result_image is not None:
        cv2.imwrite(output_path, result_image)
        print(f"Inpainting successful! Result saved to {output_path}")
    else:
        print("Inpainting failed.")