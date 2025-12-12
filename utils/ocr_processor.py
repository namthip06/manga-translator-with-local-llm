import logging
from paddleocr import PaddleOCR

class OCRProcessor:
    def __init__(self, use_angle_cls=True, lang='en', log_level=logging.INFO):
        """
        Initialize the OCRProcessor with PaddleOCR.
        
        Args:
            use_angle_cls (bool): Whether to use angle classification.
            lang (str): Language code (e.g., 'en', 'ch', 'japan', 'korean').
            log_level (int): Logging level.
        """
        # Suppress PaddleOCR logging if needed, or configure it
        self.ocr = PaddleOCR(use_doc_orientation_classify=use_angle_cls, 
                            use_doc_unwarping=False, 
                            use_textline_orientation=False,
                            lang=lang)
        logging.basicConfig(level=log_level)
        self.logger = logging.getLogger(__name__)

    def perform_ocr(self, image_path):
        """
        Perform OCR on the given image and return the extracted text sorted by reading order.
        
        Args:
            image_path (str): Path to the image file.
            
        Returns:
            list: A list of extracted text strings.
        """
        self.logger.info(f"Processing image: {image_path}")
        result = self.ocr.predict(image_path)
        
        if not result or result[0] is None:
            self.logger.warning("No text detected.")
            return []

        # PaddleOCR result structure: result[0] is a list of [box, (text, confidence)]
        # box: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        print("rec_polys : ", len(result[0]['rec_polys']))
        print("rec_texts : ", len(result[0]['rec_texts']))
        
        raw_boxes = result[0]['rec_polys']
        raw_texts = result[0]['rec_texts']
        # print("raw_boxes : ", raw_boxes)
        
        # Combine to keep association: (box, text_data)
        combined_data = list(zip(raw_boxes, raw_texts))
        
        # Returns List of groups (List[List[(Box, Text)]])
        sorted_groups = self._sort_boxes(combined_data)
        
        # Separate into two lists preserving group structure
        grouped_boxes = []
        grouped_texts = []
        
        for group in sorted_groups:
            # group is a list of (box, text)
            b_group = [item[0] for item in group]
            t_group = [item[1] for item in group]
            grouped_boxes.append(b_group)
            grouped_texts.append(t_group)
        
        return grouped_boxes, grouped_texts

    def _sort_boxes(self, items, y_threshold=20):
        """
        Sort bounding boxes based on Y coordinate and group them by proximity.
        
        Args:
            items (list): List of (box, text) tuples. 
            y_threshold (int): proper distance to group simultaneous lines.
            
        Returns:
            list: List of groups, where each group is a list of (box, text) sorted by Y.
        """
        # Helper function to get top-left Y coordinate
        def get_y(item):
            # item is (box, text)
            box = item[0]
            # box is geometric box points [[x,y],...]
            if hasattr(box, "shape") and box.shape == (4, 2):
                return min(p[1] for p in box)
            # Fallback for standard list structure if needed
            return min(p[1] for p in box[0])

        # Initial sort by Y
        # items is a list of tuples, so tolist check is not needed/applicable for the outer list
        # Ensure items is a list
        if not isinstance(items, list):
             items = list(items)
             
        items = sorted(items, key=get_y)
        
        grouped_boxes = []
        
        if not items:
            return grouped_boxes
            
        # Initialize first group
        current_group = [items[0]]
        # Reference Y is the Y of the first box in the current group
        last_y = get_y(items[0])
        
        for i in range(1, len(items)):
            item = items[i]
            y = get_y(item)
            
            # Check if the current box is in the same group (close Y)
            # print("abs(y - last_y) : ", abs(y - last_y))
            if abs(y - last_y) <= y_threshold:
                current_group.append(item)
            else:
                # End of current group
                grouped_boxes.append(current_group)
                
                # Start new group
                current_group = [item]
                last_y = y
                
        # Append the last group
        if current_group:
            grouped_boxes.append(current_group)
            
        return grouped_boxes

# Example usage (commented out to avoid auto-execution impact on import):
if __name__ == "__main__":
    processor = OCRProcessor()
    grouped_boxes, grouped_texts = processor.perform_ocr("./output_scraper/potential villain.jpg")
    print("--- Grouped Texts ---")
    for i, text_group in enumerate(grouped_texts):
        print(f"Group {i}: {text_group}")
        
    # print("--- Grouped Boxes ---")
    # for i, box_group in enumerate(grouped_boxes):
    #     print(f"Group {i}: {box_group}")    