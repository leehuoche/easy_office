import os

import paddleocr
import docx

# Paddleocr supports Chinese, English, French, German, Korean and Japanese.
# You can set the parameter `lang` as `ch`, `en`, `fr`, `german`, `korean`, `japan`
# to switch the language model in order.
ocr = paddleocr.PaddleOCR(use_angle_cls=True, lang='ch') # need to run only once to download and load model into memory

def is_image_file(file_name):
    valid_suffix= [".jpg", ".JPG", ".png", ".PNG"]
    for v in valid_suffix:
        if file_name.endswith(v):
            return True
    return False

def list_path_file(path):
    file_list=[]
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            # print(os.path.join(root, name))
            if is_image_file(name):
                file_list.append(os.path.join(root, name))
    return file_list

def ocr_images(img_path):
    result = ocr.ocr(img_path, cls=True)
    return result

def parse_result(result, document):
    for line in result:
        last=line[-1]
        paragraph=last[0]
        print(last[0])
        #print(line)
        p = document.add_paragraph(paragraph)

def parse_images_in_dir(files):
    for f in files:
        print("process image:" + f)
        document = docx.Document()
        result = ocr_images(f)
        parse_result(result, document)
        doc_dir = "../output/"
        doc_name = os.path.basename(f)
        doc_name = doc_name.replace('.', '_')
        doc_path = doc_dir + doc_name + ".docx"
        document.save(doc_path)
        # print(result)

def main():
    path="../images"
    files = list_path_file(path)
    parse_images_in_dir(files)


if __name__ == '__main__':
    main()