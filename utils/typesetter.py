import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

class Typesetter:
    def __init__(self, font_path=None):
        """
        Initialize the Typesetter with a specific font.
        Tries to locate a Thai-compatible font if not provided.
        """
        if font_path and os.path.exists(font_path):
            self.font_path = font_path
        else:
            # Common Windows fonts that support Thai
            # Tahoma is widely available and supports Thai well.
            # Leelawadee is another option.
            possible_fonts = [
                "C:/Windows/Fonts/tahoma.ttf",
                "C:/Windows/Fonts/LeelawUI.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/seguiemj.ttf" 
            ]
            self.font_path = "arial.ttf" # Default fallback
            for f in possible_fonts:
                if os.path.exists(f):
                    self.font_path = f
                    break
        
    def overlay_text(self, image_path, grouped_boxes, grouped_texts, output_path=None):
        """
        Overlays new text onto the image using the bounding boxes from PaddleOCR.
        
        Args:
            image_path (str): Path to the original image.
            grouped_boxes (list): List of groups of boxes (from PaddleOCR).
                                  Each box is [[x1, y1], [x2, y2], [x3, y3], [x4, y4]].
            grouped_texts (list): List of groups of text strings to write.
            output_path (str, optional): Path to save the output image.
            
        Returns:
            Image: The PIL Image object with text drawn.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        try:
            image = Image.open(image_path).convert("RGBA")
        except Exception as e:
            print(f"Failed to load image: {e}")
            return None

        draw = ImageDraw.Draw(image)

        # Loop through groups
        for boxes, texts in zip(grouped_boxes, grouped_texts):
            # Loop through individual items in the group
            for box, text in zip(boxes, texts):
                if not text:
                    continue
                
                # Convert box to numpy for easier min/max calc
                # box structure: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                pts = np.array(box, dtype=np.float32)
                
                min_x = np.min(pts[:, 0])
                max_x = np.max(pts[:, 0])
                min_y = np.min(pts[:, 1])
                max_y = np.max(pts[:, 1])
                
                box_width = max_x - min_x
                box_height = max_y - min_y
                
                if box_width <= 0 or box_height <= 0:
                    continue

                # Calculate best font size and wrapped lines
                font, lines = self._fit_text(text, box_width, box_height, draw)
                
                # Calculate total text block height
                total_text_height = 0
                line_heights = []
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    h = bbox[3] - bbox[1]
                    line_heights.append(h)
                    total_text_height += h
                
                # Center vertically
                current_y = min_y + (box_height - total_text_height) / 2
                
                # Draw each line
                for line, h in zip(lines, line_heights):
                    bbox = draw.textbbox((0, 0), line, font=font)
                    w = bbox[2] - bbox[0]
                    # Center horizontally
                    x = min_x + (box_width - w) / 2
                    
                    # Draw text with black fill (assuming light background or cleared text)
                    # Use a small stroke for visibility if needed, but standard manga is just black on white/cleaned.
                    draw.text((x, current_y), line, font=font, fill="black")
                    current_y += h
        
        image = image.convert("RGB")
        if output_path:
            image.save(output_path)
            
        return image

    def _fit_text(self, text, max_width, max_height, draw):
        """
        Finds the largest font size such that the text, when wrapped, fits within the max_width and max_height.
        """
        min_size = 10
        max_size = 100
        best_font = ImageFont.truetype(self.font_path, min_size)
        best_lines = [text]
        
        # Binary search for font size
        low = min_size
        high = max_size
        
        while low <= high:
            mid = (low + high) // 2
            try:
                font = ImageFont.truetype(self.font_path, mid)
            except:
                font = ImageFont.load_default()
            
            lines = self._wrap_text(text, font, max_width, draw)
            
            # Calculate total height
            total_h = 0
            fits_width = True
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                total_h += h
                if w > max_width:
                    fits_width = False
            
            if total_h <= max_height and fits_width:
                # fits, try larger
                best_font = font
                best_lines = lines
                low = mid + 1
            else:
                # too big, try smaller
                high = mid - 1
                
        return best_font, best_lines

    def _wrap_text(self, text, font, max_width, draw):
        """
        Wraps text to fit within max_width.
        """
        lines = []
        words = text.split(' ') # Simple space splitting
        
        # Determine if we need to split by characters (e.g. for long Thai strings without spaces)
        # If a single word is wider than max_width, we might force split.
        
        current_line = []
        
        def get_width(t):
            return draw.textlength(t, font=font)

        for word in words:
            # Check if adding this word exceeds width
            test_line = ' '.join(current_line + [word])
            if get_width(test_line) <= max_width:
                current_line.append(word)
            else:
                # Push current line if valid
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # The word itself is too long, we must split it
                    # This handles the case of "longstring" or Thai text without spaces
                    # We'll split by character for this 'word'
                    chars = list(word)
                    sub_line = ""
                    for char in chars:
                        if get_width(sub_line + char) <= max_width:
                            sub_line += char
                        else:
                            lines.append(sub_line)
                            sub_line = char
                    current_line = [sub_line]
        
        if current_line:
            lines.append(' '.join(current_line))
            
        return lines

if __name__ == "__main__":
    # Test Setup
    
    # 1. Define paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir) # assumes utils is one level deep
    # Use an image that matches the coordinate scale (approx 1600x1200 or similar based on coords)
    image_path = os.path.join(project_root, "output_scraper", "potential villain.jpg")
    
    # Check if image exists, if not use a dummy mock
    if not os.path.exists(image_path):
        print(f"Warning: Image not found at {image_path}. Please provide a valid image path to test.")
        # Create a dummy image for testing - make it large enough for the boxes
        dummy_path = "test_image.jpg"
        dummy_img = Image.new('RGB', (1600, 1000), color='white')
        dummy_img.save(dummy_path)
        image_path = dummy_path
        print(f"Created dummy image at {dummy_path}")

    # 2. Mock Data (User provided structure)
    grouped_boxes = [
        [[[510, 94], [1154, 94], [1154, 139], [510, 139]]], 
        [[[24, 155], [184, 153], [184, 192], [24, 194]], [[27, 204], [485, 204], [485, 238], [27, 238]], [[28, 253], [524, 253], [524, 284], [28, 284]]], 
        [[[1150, 168], [1481, 168], [1481, 192], [1150, 192]], [[1150, 203], [1543, 203], [1543, 227], [1150, 227]], [[1150, 237], [1539, 237], [1539, 261], [1150, 261]], [[1151, 272], [1565, 272], [1565, 295], [1151, 295]], [[1149, 304], [1362, 304], [1362, 331], [1149, 331]], [[1150, 341], [1433, 341], [1433, 365], [1150, 365]]], 
        [[[1146, 606], [1581, 606], [1581, 637], [1146, 637]], [[1146, 649], [1533, 649], [1533, 679], [1146, 679]], [[1148, 694], [1584, 694], [1584, 721], [1148, 721]], [[1148, 738], [1338, 738], [1338, 766], [1148, 766]], [[1148, 781], [1546, 781], [1546, 813], [1148, 813]], [[1146, 824], [1373, 826], [1373, 861], [1146, 859]]], 
        [[[30, 683], [519, 683], [519, 713], [30, 713]], [[30, 728], [579, 728], [579, 755], [30, 755]], [[29, 770], [557, 770], [557, 801], [29, 801]]]
    ]
    
    grouped_texts = [
        ['MEET POTENTIAL VILLAIN'], 
        ['0 FEATS', '0 STRATEGIC VICTORIES', '38 AURAFARMING SCENES'], 
        ['THERESA WE NEED TO', 'HAVE ANOTHER CIVIL WAR', 'IM BEGGING THE MILITARY', 'INDUSTRIAL COMPLEX PAYS', 'BIG GLORY TO', 'LOCKHEED MARTIN'], 
        ['IS IMMEDIATELY CLAPPED', 'THE MICROSECOND HE', 'MEETS ANYONE SLIGHTLY', 'STRONGER', '(GIVE ME STREET TIERS', 'NOOO NOOO)'], 
        ['GIVE ME AMNANNAM PLEASE', 'PLEASE I NEED IT FOR THE SAKE', 'OF KAZDEL OR SOMETHING IDK']
    ]

    # Verify matching lengths
    assert len(grouped_boxes) == len(grouped_texts), "Boxes and texts groups must match in length"
    for i, (b_group, t_group) in enumerate(zip(grouped_boxes, grouped_texts)):
        assert len(b_group) == len(t_group), f"Group {i} mismatch: {len(b_group)} boxes vs {len(t_group)} texts"

    # 3. Initialize Typesetter
    typesetter = Typesetter() # Will auto-detect font
    
    print(f"Using font: {typesetter.font_path}")
    
    # 4. Run Overlay
    output_path = "test_output.jpg"
    result_img = typesetter.overlay_text(image_path, grouped_boxes, grouped_texts, output_path)
    
    if result_img:
        print(f"Success! Image saved to {output_path}")
    else:
        print("Failed to generate image.")
