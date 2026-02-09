"""
VLM-based PDF Parser using Ollama.

Uses pdf2image to convert pages to images and a Vision Language Model
to extract text preserving layout logic.
"""
import base64
import logging
from io import BytesIO
from typing import List, Union

import pdf2image
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from app.core.config import OLLAMA_VISION_MODEL, OLLAMA_HOST

from app.db.session import SessionLocal
from app.db.models import Prompt

logger = logging.getLogger(__name__)


class VLMPDFParser:
    """Parses PDF documents using a Vision Language Model (VLM)."""

    DEFAULT_PROMPT = """
    Analyze this image of a document page. 
    Extract all the text content exactly as it appears, preserving the structure.
    
    - If there are tables, represent them as Markdown tables.
    - If there are headers, use Markdown headers (#).
    - If there are lists, use Markdown lists.
    - Do not add any conversational text (like "Here is the text").
    - Just output the markdown content.
    """

    def __init__(self, model_name: str = OLLAMA_VISION_MODEL):
        self.model_name = model_name
        self.llm = ChatOllama(
            model=model_name,
            temperature=0.1,
        )
        self.prompt = self._get_prompt()

    def _get_prompt(self) -> str:
        """Fetch prompt from database or create default."""
        db = SessionLocal()
        try:
            prompt_obj = db.query(Prompt).filter(Prompt.key == "vision_pdf_extraction").first()
            if prompt_obj:
                logger.debug("Loaded 'vision_pdf_extraction' prompt from DB")
                return prompt_obj.template
            
            # Create default if not exists
            logger.info("Creating default 'vision_pdf_extraction' prompt in DB")
            new_prompt = Prompt(
                key="vision_pdf_extraction",
                template=self.DEFAULT_PROMPT,
                required_placeholders=[]
            )
            db.add(new_prompt)
            db.commit()
            return self.DEFAULT_PROMPT
        except Exception as e:
            logger.error(f"Error fetching prompt from DB: {e}")
            return self.DEFAULT_PROMPT
        finally:
            db.close()

    def _convert_to_base64(self, image) -> str:
        """Convert PIL Image to base64 string."""
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def parse(self, file_path: str) -> str:
        """Parse a PDF file and return the extracted text."""
        logger.info(f"Parsing PDF with VLM ({self.model_name}): {file_path}")
        
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_path(file_path)
            logger.info(f"Converted PDF to {len(images)} images")
            
            full_text = []
            
            for i, image in enumerate(images):
                logger.info(f"Processing page {i+1}/{len(images)}...")
                
                # Prepare message for VLM
                base64_image = self._convert_to_base64(image)
                
                message = HumanMessage(
                    content=[
                        {"type": "text", "text": self.prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                        },
                    ]
                )
                
                # Invoke LLM
                response = self.llm.invoke([message])
                page_content = response.content
                
                full_text.append(f"<!-- Page {i+1} -->\n{page_content}")
                
            return "\n\n".join(full_text)
            
        except Exception as e:
            logger.error(f"Error parsing PDF with VLM: {e}")
            raise
