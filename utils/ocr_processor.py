import logging
import os
from PIL import Image
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
        
        # Check and convert image if necessary
        file_ext = os.path.splitext(image_path)[1].lower()
        supported_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.pdf']
        
        if file_ext not in supported_exts:
            self.logger.info(f"Unsupported file format {file_ext}. Converting to PNG...")
            try:
                img = Image.open(image_path).convert("RGB")
                new_image_path = os.path.splitext(image_path)[0] + ".png"
                img.save(new_image_path, "PNG")
                self.logger.info(f"Saved converted image to: {new_image_path}")
                image_path = new_image_path
            except Exception as e:
                self.logger.error(f"Failed to convert image {image_path}: {e}")
                return [], []

        result = self.ocr.predict(image_path)
        
        if not result or result[0] is None:
            self.logger.warning("No text detected.")
            return []

        # PaddleOCR result structure: result[0] is a list of [box, (text, confidence)]
        # box: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        
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

    def _sort_boxes(self, items, x_threshold=20, y_threshold=20):
        """
        Sorts (groups) boxes using spatial clustering.
        Combines boxes that are close to each other (in both X and Y) into a single "balloon".
        
        Args:
            items (list): List of (box, text) tuples.
            x_threshold (int): Maximum horizontal gap to consider as connected.
            y_threshold (int): Maximum vertical gap to consider as connected.
            
        Returns:
            list: List of groups, where each group is a list of (box, text) sorted by reading order.
        """
        if not items:
            return []

        # 1. Prepare data: Calculate bounding rect (min_x, min_y, max_x, max_y) for each box
        # We keep track of indices to merge them later
        n = len(items)
        rects = []
        for i, (box, text) in enumerate(items):
            # box is a 2D array-like of 4 points: [[x1, y1], ..., [x4, y4]]
            # convert to list of points to handle both numpy and list types
            if hasattr(box, "tolist"):
                points = box.tolist()
            else:
                points = box
            
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            
            rects.append({
                'index': i,
                'min_x': min(xs),
                'max_x': max(xs),
                'min_y': min(ys),
                'max_y': max(ys)
            })

        # 2. Build Adjacency Graph
        # We use an adjacency list: graph[i] = [list of connected indices]
        adj = [[] for _ in range(n)]
        
        for i in range(n):
            for j in range(i + 1, n):
                r1 = rects[i]
                r2 = rects[j]
                
                # Calculate gaps
                def get_gap(start1, end1, start2, end2):
                    # Gap is distance between closest edges. Overlap means gap is 0.
                    gap = max(start1, start2) - min(end1, end2)
                    return max(0, gap)

                x_gap = get_gap(r1['min_x'], r1['max_x'], r2['min_x'], r2['max_x'])
                y_gap = get_gap(r1['min_y'], r1['max_y'], r2['min_y'], r2['max_y'])
                
                # Check thresholds
                if x_gap <= x_threshold and y_gap <= y_threshold:
                    adj[i].append(j)
                    adj[j].append(i)

        # 3. Find Connected Components (BFS)
        visited = [False] * n
        grouped_items = []
        
        for i in range(n):
            if not visited[i]:
                # Start a new component
                component_indices = []
                stack = [i]
                visited[i] = True
                while stack:
                    curr = stack.pop()
                    component_indices.append(curr)
                    for neighbor in adj[curr]:
                        if not visited[neighbor]:
                            visited[neighbor] = True
                            stack.append(neighbor)
                
                # Collect items for this component
                # Sort items within the group by Y primarily (Top-to-Bottom reading)
                component_indices.sort(key=lambda idx: rects[idx]['min_y'])
                
                component = [items[idx] for idx in component_indices]
                grouped_items.append(component)

        # 4. Sort the groups themselves by their top-most coordinate
        def get_group_y(group):
            # Find global min_y of the group
            min_y = float('inf')
            for item in group:
                box = item[0]
                if hasattr(box, "tolist"):
                    points = box.tolist()
                else:
                    points = box
                current_min = min(p[1] for p in points)
                if current_min < min_y:
                    min_y = current_min
            return min_y

        grouped_items.sort(key=get_group_y)

        return grouped_items

# Example usage (commented out to avoid auto-execution impact on import):
if __name__ == "__main__":
    processor = OCRProcessor()
    
    # Specify the folder path containing images
    folder_path = "./output_scraper\Kagurabachi, Chapter 105 - Kagurabachi Manga Online"  # You can change this to your target folder
    
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        print(f"Processing images in folder: {folder_path}")
        
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
        
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(valid_extensions):
                image_path = os.path.join(folder_path, filename)
                print(f"\n--- Processing: {filename} ---")
                
                try:
                    grouped_boxes, grouped_texts = processor.perform_ocr(image_path)
                    
                    print("--- Grouped Texts ---")
                    
                    for i, group in enumerate(grouped_texts):
                        # group is a list of tuples (text, confidence) usually, or just text?
                        # Based on line 59: t_group = [item[1] for item in group]
                        # And line 47 combined_data = list(zip(raw_boxes, raw_texts))
                        # paddleocr result[0]['rec_texts'] is usually just a list of (text, confidence) tuples.
                        # So item[1] in line 59 would be the (text, confidence) tuple if raw_texts elements are (text, conf).
                        # Wait, let's look at `paddleocr` docs or common usage. 
                        # Usually `ocr.predict` (or just `ocr.ocr`) returns `[[[box], (text, conf)], ...]`.
                        # But here `result = self.ocr.predict(image_path)`.
                        # The code at line 43 says `raw_texts = result[0]['rec_texts']`.
                        # This implies `predict` returns a dict-like structure or similar.
                        # Assuming the existing code works, `grouped_texts` contains lists of whatever `raw_texts` contains.
                        # If `raw_texts` contains strings, then `group` contains strings.
                        # If `raw_texts` contains (text, conf), then `group` contains (text, conf).
                        # Let's just print the group content to be safe.
                        print(f"Group {i+1}: {group}")

                except Exception as e:
                    print(f"Error processing {filename}: {e}")
    else:
        print(f"Folder not found: {folder_path}")