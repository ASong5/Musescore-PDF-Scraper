from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from requests import get
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF
import os
from pypdf import PdfMerger
import pathlib
from PIL import Image
from tqdm import tqdm

def extract_numeric_part(pdf):
    return int(pdf.split('.')[0])

service = Service(executable_path="/usr/lib/chromium-browser/chromedriver")

chrome_options = Options()
chrome_options.binary_location = '/usr/bin/chromium-browser'
chrome_options.add_argument("--headless")
chrome_options.add_argument('window-size=1024x768')

driver = webdriver.Chrome(service=service, options=chrome_options)
driver.maximize_window()

scoreUrl = input("Enter the musescore URL: ")

driver.get(scoreUrl)

WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "jmuse-scroller-component")))

scrollable_element = driver.find_element(By.ID, "jmuse-scroller-component")

elems = scrollable_element.find_elements(By.XPATH, "./div")
title = driver.find_element(By.XPATH, "//meta[@property='og:title']").get_attribute("content")

total_elements = len(elems) - 1

outer_progress_bar = tqdm(total=total_elements, desc="Compiling Score..", unit="pdfs", colour="magenta", leave=False)

for idx, child in enumerate(elems, start=1):
    try:
        driver.execute_script("arguments[0].scrollIntoView();", child)
        start_time = time.time()
        time.sleep(.2)
        elapsed_time = time.time() - start_time

        inner_progress_bar = tqdm(total=1, initial=1, desc=f"Processing... {idx}", colour="blue", leave=False)

        with open(f"{idx}", "wb") as file:
            res = get(child.find_element(By.XPATH, "./img").get_attribute("src"))
            file.write(res.content)
            if res.headers["Content-Type"] == "image/svg+xml":
                drawing = svg2rlg(f"{idx}")
                renderPDF.drawToFile(drawing, f"{idx}.pdf")
            else:
                img = Image.open(f"{idx}")
                img.save(f"{idx}.pdf")
            file.close()
        os.remove(f"{idx}")

        inner_progress_bar.close()

    except Exception as e:
        os.remove(f"{idx}")
        inner_progress_bar.close()
        outer_progress_bar.update(1)
        break
    finally:
        remaining_elements = total_elements - idx
        estimated_remaining_time = elapsed_time * remaining_elements
        outer_progress_bar.set_postfix(remaining_time=f"{estimated_remaining_time:.2f} seconds")
        outer_progress_bar.update(1)
        
outer_progress_bar.close()

pdfs = sorted([x for x in os.listdir() if x.endswith(".pdf")], key=extract_numeric_part)

merger = PdfMerger()

merge_progress_bar = tqdm(total=len(pdfs), desc="Merging PDFs..", unit="pdfs", colour="magenta", leave=False)
for pdf in pdfs:
    merger.append(pdf)
    merge_progress_bar.update(1)
merge_progress_bar.close()

merger.write(f"{title}.pdf")
merger.close()

pathlib.Path("./PDFs").mkdir(parents=True, exist_ok=True)
os.rename(f"{title}.pdf", f"./PDFs/{title}.pdf")

deletion_progress_bar = tqdm(total=len(pdfs), desc="Cleaning Up...", unit="pdfs", colour="magenta", leave=False)
for pdf in pdfs:
    os.remove(pdf)
    deletion_progress_bar.update(1)
deletion_progress_bar.close()

driver.quit()
