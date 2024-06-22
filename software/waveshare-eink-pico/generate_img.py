from PIL import Image, ImageDraw, ImageFont
import numpy as np

EPD_WIDTH       = 400
EPD_HEIGHT      = 300

#multiline text with automatic line breaking
def draw_multiline_text(draw, text, position, font, max_width):
    # Split the text into words
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        # Check if adding the word would exceed the max width
        test_line = ' '.join(current_line + [word])
        test_line_width = draw.textbbox((0, 0), test_line, font=font)[2]
        if test_line_width <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]

    # Add the last line
    lines.append(' '.join(current_line))

    # Draw each line
    y = position[1]
    for line in lines:
        draw.text((position[0], y), line, font=font, fill="black")
        y += draw.textbbox((0, 0), line, font=font)[3]

def generate_image(product_name="Produktname", price=0, description="", supplier="", bottom_text=""):
    # Create a new image with a white background
    width, height = EPD_WIDTH, EPD_HEIGHT
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    def is_non_empty_string(variable):
        return isinstance(variable, str) and len(variable) > 0
    price = f"{price:.2f}".replace(".",",")
    if not is_non_empty_string(description): description = ""
    if not is_non_empty_string(supplier): supplier = ""
    

    multiline_text = description #"Ein Rosinenbrötchen ist ein fluffiges, süßes Gebäck, das mit saftigen Rosinen gespickt ist. Es bietet einen köstlichen Kontrast zwischen dem weichen Teig und den fruchtigen Rosinen, perfekt für ein Frühstück oder eine gemütliche Kaffeepause."

    # Load a font
    font = ImageFont.truetype("material/arial.ttf", 40)
    font_b = ImageFont.truetype("material/arialbd.ttf", 40)
    font_mitte = ImageFont.truetype("material/arialbd.ttf", 25)
    small_font = ImageFont.truetype("material/arial.ttf", 15)
    extra_small_font = ImageFont.truetype("material/arial.ttf", 12)

    price_bbox = draw.textbbox((0, 0), price, font=font)
    price_width = price_bbox[2] - price_bbox[0]
    price_height = price_bbox[3] - price_bbox[1]
    price_x = (width - price_width) - 10
    price_y = height - price_height *(1+1/5)
    draw.text((price_x, price_y), price, fill="black", font=font_b)

    # Multiline Product Name
    multiline_text_x = 2
    multiline_text_y = 2  # Adjust vertical position as needed
    max_text_width = width - 10-multiline_text_x  # Define the maximum width for the text
    draw_multiline_text(draw, product_name, (multiline_text_x, multiline_text_y), font_b, max_text_width)

    # Beschreibung
    multiline_text_x = 2
    multiline_text_y = 90
    max_text_width = width - 4  # Define the maximum width for the text
    draw_multiline_text(draw, multiline_text, (multiline_text_x, multiline_text_y), small_font, max_text_width)

    if supplier == "Kern & Korn":
        # Backtag
        multiline_text_x = 110
        multiline_text_y = 190
        max_text_width = width - 4-110  # Define the maximum width for the text
        draw_multiline_text(draw, "Backtag und Haltbarkeit: siehe Verpackung", (multiline_text_x, multiline_text_y), extra_small_font, max_text_width)

        # Zutaten
    #    multiline_text_x = 110
    #    multiline_text_y = 210
    #    max_text_width = width - 4-110  # Define the maximum width for the text
    #    draw_multiline_text(draw, "Zutaten: Mehl, Wasser, Gerste, Hopfen", (multiline_text_x, multiline_text_y), extra_small_font, max_text_width)

        # Load the additional image
        additional_image_path = "material/20200222_KernundKorn_Logo_rund_weiß-auf-schwarz_R.png"  # Replace with your image path
        additional_image = Image.open(additional_image_path)
        # Resize the additional image if needed
        additional_image.thumbnail((100, 100))  # Adjust the size as needed
        # Calculate position for the additional image (top right corner)
        # Paste the additional image onto the main image
        additional_image_x = 0
        additional_image_y = 300-additional_image.height
        image.paste(additional_image, (additional_image_x, additional_image_y), additional_image)


    draw.text((150, height-24), bottom_text, fill="black", font=small_font)


    ## Save the image
    #image.save("price_tag_with_image.png")

    # Convert the image to grayscale
    image_gray = image.convert("L")

    # Convert the grayscale image to a NumPy array
    image_array = np.array(image_gray)

    return image_array


def process_image_to_string(image_array):
    output = []

    # map 256 grayscale to 2bit grayscale
    # https://stackoverflow.com/questions/12589923/slicing-numpy-array-with-another-array
    def map_values(values):
        mapped_values = np.zeros_like(values)
        mapped_values[(191 <= values) ] = 3
        mapped_values[(128 <= values) & (values <= 190)] = 2
        mapped_values[(64 <= values) & (values <= 127)] = 1
        return mapped_values
    image = map_values(image_array)

    #slice matrix into vectors of size 4
    sliced_vectors = []
    slice_size = 4
    for row in image:
        num_full_sub_vectors = len(row) // slice_size
        full_sub_vectors = row[:num_full_sub_vectors*slice_size].reshape(-1, slice_size)
        # Append full sub-vectors
        for vec in full_sub_vectors:
            sliced_vectors.append(vec)

    #objective: put 4x 2bit value into one byte
    weight_vector = np.array([64, 16, 4, 1])

    # calculate_dot_products
    for vec in sliced_vectors:
        dot_product = np.dot(vec, weight_vector)
        output.append(f"{dot_product}")

    return '\n'.join(output)+'\n'


def process_image_to_string_slow(image_array):
    output = []

    for y in range(EPD_HEIGHT):
        for x in range(0, EPD_WIDTH, 4):
            if x >= image_array.shape[1] or y >= image_array.shape[0]:
                output.append("0\n")
            else:
                b = 0
                for i in range(4):
                    v = image_array[y][x+i]
                    if v >= 255 - 64:
                        v_out = 3
                    elif v >= 128:
                        v_out = 2
                    elif v >= 64:
                        v_out = 1
                    else:
                        v_out = 0
                    b = b * 4 + v_out
                output.append(f"{b}\n")

    return ''.join(output)


def get_product_file(product_name="Produktname", price=0, description="", supplier="", bottom_text=""):
    img = generate_image(product_name, price, description, supplier, bottom_text)
    t = process_image_to_string(img)
    return t


if __name__ == "__main__":
    img = generate_image("Neues Produkt")
    t = process_image_to_string(img)

#    with open("t.txt", "w") as text_file:
#        text_file.write(t)

