import easyocr
import docx

document = docx.Document()

reader = easyocr.Reader(['ch_sim','en'])
result = reader.readtext('../images/3.jpg')

for i in result:
    paragraph = i[-2]
    print(paragraph)
    p = document.add_paragraph(paragraph)

document.save('../output/demo.docx')