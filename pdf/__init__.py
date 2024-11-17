import boto3
import tempfile
from config import *
from pyppeteer import launch
from pdf.htmlTemplate import htmlTemplate
from interfaces import InvoiceData as Input, Output


class Compute:
    def __init__(self, input: Input) -> None:
        self.input = input
        self.bucket_name = "sukoon-media"
        self.client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )

    async def upload_to_s3(self, file_path: str, file_name: str) -> str:
        metadata = {"fieldName": "pdf_file"}

        with open(file_path, "rb") as file:
            file = file.read()
            self.client.upload_fileobj(
                file,
                self.bucket_name,
                file_name,
                ExtraArgs={
                    "Metadata": metadata,
                    "ACL": "public-read",
                    "ContentType": "application/pdf"
                }
            )

    async def generate_pdf(self, html_content: str, output_path: str) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            browser = await launch(userDataDir=temp_dir, executablePath="/usr/bin/chromium-browser", args=['--no-sandbox'])
            page = await browser.newPage()
            await page.setContent(html_content, {'waitUntil': 'networkidle0'})
            await page.pdf({'path': output_path, 'format': 'A4', 'printBackground': True})
            await browser.close()
            await self.upload_to_s3(output_path, output_path.split("/")[-1])

    async def compute(self) -> Output:
        html_content = htmlTemplate(self.input)
        file_name = f"{self.input.userId}-{self.input.invoiceNumber}.pdf"
        output_path = f"/tmp/{file_name}"
        endpoint_url = self.client.meta.endpoint_url
        file_url = f"{endpoint_url}/{self.bucket_name}/invoices/{file_name}"

        await self.generate_pdf(html_content, output_path)

        return Output(
            output_status="SUCCESS",
            output_details={"file_url": file_url},
            output_message="Successfully generated Invoice PDF"
        )
