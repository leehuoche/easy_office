from paddleocr import PaddleOCR,draw_ocr
import docx

document = docx.Document()

# Paddleocr supports Chinese, English, French, German, Korean and Japanese.
# You can set the parameter `lang` as `ch`, `en`, `fr`, `german`, `korean`, `japan`
# to switch the language model in order.
ocr = PaddleOCR(use_angle_cls=True, lang='ch') # need to run only once to download and load model into memory
img_path = '../images/test2.jpg'
result = ocr.ocr(img_path, cls=True)

for line in result:
    last=line[-1]
    paragraph=last[0]
    print(last[0])
    #print(line)
    p = document.add_paragraph(paragraph)

document.save('../output/demo1.docx')