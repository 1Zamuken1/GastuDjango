import sys
try:
    from PIL import Image
except ImportError:
    print("Pillow not installed. Please install it.")
    sys.exit(1)

def remove_background(input_path, output_path, bg_color=None):
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()
    
    if bg_color is None:
        bg_color = datas[0]
    
    newData = []
    for item in datas:
        # If the pixel is similar to the background color, make it transparent
        if abs(item[0] - bg_color[0]) < 40 and \
           abs(item[1] - bg_color[1]) < 40 and \
           abs(item[2] - bg_color[2]) < 40:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)

    img.putdata(newData)
    img.save(output_path, "PNG")
    print(f"Saved {output_path}")

remove_background(r"C:\Users\Usuario\.gemini\antigravity-ide\brain\cb4615a2-233a-4146-b6fc-2c121cdd1cec\owl_500_magenta_1779836932832.png", r"c:\Users\Usuario\Downloads\GastuDjango\static\img\owl_500_fixing.png")
