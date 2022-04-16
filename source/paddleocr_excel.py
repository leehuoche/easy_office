import os

import cv2
import paddleocr

def parse_excel_imag(table_engine, save_folder, img_path):
    img = cv2.imread(img_path)
    result = table_engine(img)
    paddleocr.save_structure_res(result, save_folder,os.path.basename(img_path).split('.')[0])


def main():
    table_engine = paddleocr.PPStructure(show_log=True)
    save_folder = './output/table'
    img_path = '../images/00015504.jpg'
    parse_excel_imag(table_engine, save_folder, img_path)

if __name__ == '__main__':
    main()