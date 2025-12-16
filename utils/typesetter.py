import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

class Typesetter:
    def __init__(self, font_name=None):
        """
        Initialize the Typesetter.
        
        Args:
            font_name (str, optional): 
                Name of the font file to use (e.g., "myfont.ttf").
                If None, tries to find any font in ./fonts/ folder.
                If not found, falls back to system fonts.
        """
        # Define paths
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(base_dir)
        self.fonts_dir = os.path.join(self.project_root, "fonts")
        
        self.font_path = None

        # Try to set the requested font or a default one
        self.set_font(font_name)

    def get_available_fonts(self):
        """
        Returns a list of font filenames found in the ./fonts directory.
        """
        if not os.path.exists(self.fonts_dir):
            return []
        
        fonts = [f for f in os.listdir(self.fonts_dir) if f.lower().endswith(('.ttf', '.otf'))]
        return sorted(fonts)

    def set_font(self, font_name):
        """
        Sets the current font to the specified font name found in ./fonts 
        or a specific path.
        """
        # 1. Try: specific path provided and exists
        # if font_name and os.path.exists(font_name):
        #     self.font_path = font_name
        #     return

        # 2. Try: filename in ./fonts
        if font_name:
            candidate = os.path.join(self.fonts_dir, font_name)
            if os.path.exists(candidate):
                self.font_path = candidate
                return
            else:
                print(f"Warning: Font '{font_name}' not found in {self.fonts_dir}")

        # 3. Try: Any font in ./fonts (if font_name was None or not found)
        available = self.get_available_fonts()
        if available:
            # Default to the first one found, or keep trying to find a good one?
            # Let's pick the first one.
            self.font_path = os.path.join(self.fonts_dir, available[0])
            if font_name and font_name not in available:
                 # If user asked for something specific but we fell back
                 print(f"Falling back to default font: {available[0]}")
            return

        # 4. Fallback: System fonts (Windows)
        possible_fonts = [
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/LeelawUI.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/seguiemj.ttf" 
        ]
        self.font_path = "arial.ttf" # Ultimate fallback
        for f in possible_fonts:
            if os.path.exists(f):
                self.font_path = f
                break
        print(f"Warning: No fonts found in local directory. Using system font: {self.font_path}")

    def calculate_consolidated_box(self, boxes):
        """
        Calculates the bounding box (min_x, min_y, max_x, max_y) for a group of boxes.
        It treats all the boxes in the list as a single object to find the outermost 4 corners.

        Args:
            boxes (list): A list of boxes, where each box is a list of points (e.g. [[x1,y1], [x2,y2], ...]).

        Returns:
            tuple: (min_x, min_y, max_x, max_y) of the consolidated area.
        """
        if not boxes:
            return 0, 0, 0, 0

        # Flatten all points from all boxes into a single list
        all_points = []
        for box in boxes:
            all_points.extend(box)

        if not all_points:
            return 0, 0, 0, 0

        # Convert to numpy array for efficient min/max calculation
        pts = np.array(all_points, dtype=np.float32)

        min_x = np.min(pts[:, 0])
        max_x = np.max(pts[:, 0])
        min_y = np.min(pts[:, 1])
        max_y = np.max(pts[:, 1])

        return int(min_x), int(min_y), int(max_x), int(max_y)

    def overlay_text(self, image_path: str, grouped_boxes: list, grouped_texts: list, output_path: str = None, font_name: str = None, font_size: int = None, padding: int = 0):
        """
        Overlays new text onto the image using the bounding boxes from PaddleOCR.
        
        Args:
            image_path (str): Path to the original image.
            grouped_boxes (list): List of groups of boxes (from PaddleOCR).
                                  Each box is [[x1, y1], [x2, y2], [x3, y3], [x4, y4]].
            grouped_texts (list): List of groups of text strings to write.
            output_path (str, optional): Path to save the output image.
            font_name (str, optional): Name of the font to use.
            font_size (int, optional): Fixed font size to use. If None, calculates best fit.
            padding (int, optional): Padding to reduce the text box area from the detected box.
            
        Returns:
            Image: The PIL Image object with text drawn.
        """
        if font_name:
            self.set_font(font_name)

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        try:
            image = Image.open(image_path).convert("RGBA")
        except Exception as e:
            print(f"Failed to load image: {e}")
            return None

        draw = ImageDraw.Draw(image)

        # Loop through groups
        for boxes, text in zip(grouped_boxes, grouped_texts):
             if not boxes or not text:
                 continue

             # Consolidate the box
             min_x, min_y, max_x, max_y = self.calculate_consolidated_box(boxes)
             
             # Apply padding
             min_x += padding
             min_y += padding
             max_x -= padding
             max_y -= padding
             
             box_width = max_x - min_x
             box_height = max_y - min_y
             
             if box_width <= 0 or box_height <= 0:
                 continue

             # Text is already a string in 1D list
             full_text = text
             if not full_text.strip():
                 continue

             if font_size:
                 # Use fixed font size
                 try:
                     font = ImageFont.truetype(self.font_path, font_size)
                 except:
                     font = ImageFont.load_default() # Fallback, though load_default doesn't take size usually (it's bitmap)
                     # For TrueType fallback:
                     # font = ImageFont.truetype("arial.ttf", font_size) 
                     
                 lines = self._wrap_text(full_text, font, box_width, draw)
             else:
                 # Calculate best font size and wrapped lines
                 font, lines = self._fit_text(full_text, box_width, box_height, draw)
                 
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