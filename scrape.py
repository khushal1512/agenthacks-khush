# import time
# import requests
# import xml.et.ElementTree as ET
# from bs4 import BeautifulSoup
# import html2text
# import os
# import re

# from portia import PlanBuilderV2, StepOutput, Input
# from pydantic import BaseModel, Field

# def scrape_and_convert_site(sitemap_url: str, css_selector: str, output_dir: str) -> dict:
  
#     urls = []
#     try:
#         response = requests.get(sitemap_url)
#         response.raise_for_status()
#         root = ET.fromstring(response.content)
#         namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
#         for url_element in root.findall('sm:url', namespace):
#             loc = url_element.find('sm:loc', namespace).text
#             if loc:
#                 urls.append(loc)
#         print(f"Found {len(urls)} URLs in the sitemap.")
#     except Exception as e:
#         print(f"Error fetching sitemap: {e}")
#         return {"status": "Failed", "error": str(e), "files_converted": 0}

#     converted_count = 0
#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)
        
#     for url in urls:
#         try:
#             print(f"Processing: {url}")
#             page_response = requests.get(url)
#             page_response.raise_for_status()
#             soup = BeautifulSoup(page_response.content, 'html.parser')
            
#             content_area = soup.select_one(css_selector)
#             if not content_area:
#                 print(f"  -> Warning: CSS selector '{css_selector}' not found for {url}")
#                 continue

#             title = content_area.find('h1').get_text(strip=True) if content_area.find('h1') else "Untitled"
            
#             h = html2text.HTML2Text()
#             markdown_content = h.handle(str(content_area))
            
#             frontmatter = f'---\ntitle: "{title.replace("\"", "“")}"\n---\n\n'
#             mdx_content = frontmatter + markdown_content
            
#             filename = re.sub(r'[\\/*?:"<>|]', "", url.replace("https://", "").replace('/', '_')) + ".mdx"
#             filepath = os.path.join(output_dir, filename)
            
#             with open(filepath, 'w', encoding='utf-8') as f:
#                 f.write(mdx_content)
            
#             converted_count += 1
#             print(f"  -> Saved to {filepath}")
            
#         except Exception as e:
#             print(f"  -> Error processing {url}: {e}")

#     summary = {
#         "status": "Completed",
#         "files_converted": converted_count,
#         "output_directory": os.path.abspath(output_dir)
#     }
#     print(f"\nConversion complete. Summary: {summary}")
#     return summary

# class ConversionOutput(BaseModel):
#     status: str = Field(description="The final status of the conversion process.")
#     files_converted: int = Field(description="The total number of files successfully converted.")
#     output_directory: str = Field(description="The absolute path to the folder containing the MDX files.")

# website_to_mdx_plan = (
#     PlanBuilderV2("Website Documentation to MDX Converter")
    
#     .input(
#         name="sitemap_url", 
#         description="The URL of the sitemap.xml file to crawl.",
#         default_value="https://docs.portialabs.ai/sitemap.xml"
#     )
#     .input(
#         name="css_selector",
#         description="The CSS selector for the main content area of the pages.",
#         default_value="main"
#     )
#     .input(
#         name="output_dir",
#         description="The local directory to save the converted MDX files.",
#         default_value="output_mdx"
#     )

#     .function_step(
#         step_name="scrape_and_convert",
#         function=scrape_and_convert_site,
#         args={
#             "sitemap_url": Input("sitemap_url"),
#             "css_selector": Input("css_selector"),
#             "output_dir": Input("output_dir"),
#         }
#     )

#     .final_output(output_schema=ConversionOutput)
#     .build()
# )

# from portia_client import portia
# from plans import website_to_mdx_plan

# plan_run = portia.run_plan(website_to_mdx_plan)

# print(plan_run.outputs.final_output.value)