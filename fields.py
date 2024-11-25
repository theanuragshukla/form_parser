import cv2
import numpy as np
import pytesseract
from PIL import Image
from chat_manager import ChatManager
import fitz
import json

IN_PROGRESS = []

llm = ChatManager()

def safe_int(value):
    """Safely convert any value to integer"""
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return 0
def process_form_image(image_path, output_path="image_fields.jpg", margin_percent=5):
    """
    Process form image to detect text and input fields with margin handling
    
    Args:
        image_path (str): Path to input image
        output_path (str): Path to save processed image
        margin_percent (float): Percentage of image width to use as margin (default 5%)
    """
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image from {image_path}")

    height, width = img.shape[:2]
    
    # Calculate margins
    left_margin = int(width * (margin_percent / 100))
    right_margin = width - left_margin

    # Perform OCR
    ocr_result = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    # Collect text boxes with explicit type conversion
    text_boxes = []
    texts = []

    try:
        for i in range(len(ocr_result['text'])):
            conf = safe_int(ocr_result['conf'][i])
            if conf > 30:  # Increased confidence threshold
                text = str(ocr_result['text'][i]).strip()
                if text:
                    x = safe_int(ocr_result['left'][i])
                    y = safe_int(ocr_result['top'][i])
                    w = safe_int(ocr_result['width'][i])
                    h = safe_int(ocr_result['height'][i])
                    
                    # Only include text boxes within margins
                    if left_margin <= x <= right_margin:
                        text_boxes.append((x, y, w, h))
                        texts.append(text)
    except Exception as e:
        print(f"Error processing OCR results: {str(e)}")
        return [], []

    # Group text boxes by vertical position with improved line detection
    line_groups = []
    if text_boxes:
        sorted_boxes = sorted(zip(text_boxes, texts), key=lambda x: (x[0][1], x[0][0]))
        current_line = [sorted_boxes[0]]
        current_y = sorted_boxes[0][0][1]
        
        # Adaptive line height threshold based on font size
        line_height_threshold = sorted_boxes[0][0][3] * 0.7

        for box, text in sorted_boxes[1:]:
            if abs(box[1] - current_y) < line_height_threshold:
                current_line.append((box, text))
            else:
                if len(current_line) > 0:  # Only add non-empty lines
                    line_groups.append(current_line)
                current_line = [(box, text)]
                current_y = box[1]
                line_height_threshold = box[3] * 0.7  # Update threshold for new line

        if len(current_line) > 0:  # Add the last line if not empty
            line_groups.append(current_line)

    print(f"Detected {len(line_groups)} line groups")

    # Create output image
    img_output = img.copy()
    input_fields = []

    # Draw margin guidelines (for debugging)
    cv2.line(img_output, (left_margin, 0), (left_margin, height), (128, 128, 128), 1)
    cv2.line(img_output, (right_margin, 0), (right_margin, height), (128, 128, 128), 1)

    # Process each line
    for line in line_groups:
        line_boxes = [item[0] for item in line]
        line_boxes.sort(key=lambda x: x[0])

        # Calculate group box coordinates
        group_left = min(box[0] for box in line_boxes)
        group_right = max(box[0] + box[2] for box in line_boxes)
        group_top = min(box[1] for box in line_boxes)
        group_bottom = max(box[1] + box[3] for box in line_boxes)
        
        # Add padding to group box
        padding = 2
        group_left = max(group_left - padding, left_margin)
        group_right = min(group_right + padding, right_margin)
        group_top = max(group_top - padding, 0)
        group_bottom = min(group_bottom + padding, height)

        # Draw single green box around text group
        cv2.rectangle(img_output,
                     (group_left, group_top),
                     (group_right, group_bottom),
                     (0, 255, 0), 2)

        line_height = group_bottom - group_top

        # Detect input fields
        min_field_width = line_height * 1.5  # Minimum width for input field
        max_field_width = width * 0.4  # Maximum width (40% of image width)

        if len(line_boxes) > 1:
            # Check spaces between labels
            for j in range(len(line_boxes) - 1):
                current_box = line_boxes[j]
                next_box = line_boxes[j + 1]

                space_start_x = current_box[0] + current_box[2]
                space_width = next_box[0] - space_start_x

                if space_width > min_field_width:
                    # Ensure field doesn't exceed right margin
                    actual_width = min(space_width - 10, max_field_width)
                    if space_start_x + actual_width <= right_margin:
                        input_fields.append((
                            space_start_x + 5,
                            group_top,
                            actual_width,
                            line_height
                        ))

        # Check space after last label
        last_box = line_boxes[-1]
        space_start_x = last_box[0] + last_box[2]
        space_width = right_margin - space_start_x

        if space_width > min_field_width:
            input_fields.append((
                space_start_x + 5,
                group_top,
                min(space_width - 10, max_field_width),
                line_height
            ))

    print(f"Detected {len(input_fields)} input fields")

    # Draw red boxes for input fields
    for x, y, w, h in input_fields:
        cv2.rectangle(img_output,
                     (int(x), int(y)),
                     (int(x + w), int(y + h)),
                     (0, 0, 255), 2)

    # Save the processed image
    cv2.imwrite(output_path, img_output)
    print(f"Processed image saved as {output_path}")

    # Extract grouped texts
    grouped_texts = [" ".join(text for _, text in line) for line in line_groups]

    return grouped_texts, input_fields, {
        "width": width,
        "height": height
    }

def do_the_thing(pdf_path):
    prefix = pdf_path.split(".")[0]
    IN_PROGRESS.append(prefix)
    meta={}
    imgs = []
    doc = fitz.open(pdf_path)
    for i in range(len(doc)):
        page = doc[i]
        imgpath = f"{prefix}_page_{i}.jpg"
        img = page.get_pixmap(dpi=150)
        img.save(imgpath)
        imgs.append(imgpath)
    texts = []
    fields = []

    for img in imgs:
        t, f, meta = process_form_image(img)
        texts.append(t)
        fields.append(f)

        print("\nDetected text groups:")
        arr = []
        for i, text in enumerate(t, 1):
            print(f"{i}. {text}")
            arr.append(text)
        print(f"\nNumber of input fields detected: {len(f)}")
    meta["pages"] = len(texts)
    data = {
        "meta": meta,
        "texts": texts,
        "fields": fields
    }
    with open(f"{prefix}_out.json", "w") as f:
        json.dump(data, f)
    IN_PROGRESS.pop(0)
    
    # res = llm.send_message(" ".join(arr))
    # print(f"\nResponse from chat model: {res}")

if __name__ == "__main__":

    input_image = "image1.jpg"
    try:
        t, f, meta = process_form_image(input_image)
        print("\nDetected text groups:")
        for i, text in enumerate(t, 1):
            print(f"{i}. {text}")
        print(f"\nNumber of input fields detected: {len(f)}")

    except Exception as e:
        print(f"Error processing image: {str(e)}")
        import traceback
        traceback.print_exc()
