import json
import os
import re
from typing import Any, Dict, Optional, Type

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Ollama
from pydantic import BaseModel

from .config import get_settings


def _extract_json_candidate(text: str) -> Optional[str]:
    """Try to extract a JSON block from LLM output."""

    fence_match = re.search(r"```(?:json)?(.*?)```", text, re.DOTALL | re.IGNORECASE)
    candidate = fence_match.group(1) if fence_match else text

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1:
        return None

    snippet = candidate[start : end + 1]
    snippet = snippet.replace("end_of_range=", "")
    snippet = snippet.replace(""", '"').replace(""", '"')
    return snippet.strip()


class LLMClient:
    """Wrapper around Ollama or cloud LLM for structured agent reasoning."""

    def __init__(self):
        settings = get_settings()
        
        # Check for cloud LLM API keys (priority order: Gemini, OpenAI, then others)
        gemini_api_key = os.getenv("GOOGLE_API_KEY", "").strip()
        openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY", "").strip()
        together_api_key = os.getenv("TOGETHER_API_KEY", "").strip()
        
        # Debug: Check which keys are set (without exposing values)
        if gemini_api_key:
            print(f"✅ Google Gemini API key detected (length: {len(gemini_api_key)})")
        if openai_api_key:
            print(f"✅ OpenAI API key detected (length: {len(openai_api_key)})")
        if huggingface_api_key:
            print(f"✅ Hugging Face API key detected")
        if together_api_key:
            print(f"✅ Together.ai API key detected")
        
        if gemini_api_key:
            # Use Google Gemini (free tier available, good quality)
            # Try multiple model names in order of preference
            gemini_models = [
                "gemini-1.5-pro",      # Latest stable
                "gemini-1.5-flash",    # Fast model
                "gemini-pro",           # Legacy model
                "gemini-2.5-pro"        # Very latest (may not be available)
            ]
            
            gemini_llm = None
            last_error = None
            
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                
                for model_name in gemini_models:
                    try:
                        gemini_llm = ChatGoogleGenerativeAI(
                            model=model_name,
                            google_api_key=gemini_api_key,
                            temperature=settings.temperature,
                            convert_system_message_to_human=True
                        )
                        # Test if model works by checking if it can be instantiated
                        print(f"✅ Using Google Gemini ({model_name}) for LLM")
                        self.llm = gemini_llm
                        break
                    except Exception as e:
                        last_error = e
                        print(f"⚠️  Gemini model {model_name} failed: {str(e)[:100]}")
                        continue
                
                if gemini_llm is None:
                    raise Exception(f"All Gemini models failed. Last error: {last_error}")
                    
            except ImportError as e:
                print(f"⚠️  langchain-google-genai not installed: {e}")
                print("   Install with: pip install langchain-google-genai")
                self.llm = Ollama(
                    model=settings.ollama_model,
                    temperature=settings.temperature,
                    base_url=settings.ollama_base_url,
                )
            except Exception as e:
                print(f"⚠️  Gemini setup failed: {e}")
                print("   💡 Tip: Try Hugging Face (free) or OpenAI instead")
                print("   Set HUGGINGFACE_API_KEY or OPENAI_API_KEY environment variable")
                self.llm = Ollama(
                    model=settings.ollama_model,
                    temperature=settings.temperature,
                    base_url=settings.ollama_base_url,
                )
        elif openai_api_key:
            # Use OpenAI (recommended - has free credit)
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model="gpt-3.5-turbo",
                    temperature=settings.temperature,
                    api_key=openai_api_key
                )
                print("✅ Using OpenAI for LLM")
            except ImportError:
                print("⚠️  langchain-openai not installed, falling back to Ollama")
                self.llm = Ollama(
                    model=settings.ollama_model,
                    temperature=settings.temperature,
                    base_url=settings.ollama_base_url,
                )
        elif huggingface_api_key:
            # Use Hugging Face Inference API (FREE tier available)
            try:
                from langchain_community.llms import HuggingFaceEndpoint
                self.llm = HuggingFaceEndpoint(
                    repo_id="meta-llama/Llama-3-8b-chat-hf",
                    huggingface_api_key=huggingface_api_key,
                    temperature=settings.temperature
                )
                print("✅ Using Hugging Face Inference API for LLM (FREE)")
            except ImportError:
                print("⚠️  Hugging Face not available, falling back to Ollama")
                self.llm = Ollama(
                    model=settings.ollama_model,
                    temperature=settings.temperature,
                    base_url=settings.ollama_base_url,
                )
        elif together_api_key:
            # Use Together.ai (cheapest cloud LLM)
            try:
                from langchain_together import Together
                self.llm = Together(
                    model="meta-llama/Llama-3-8b-chat-hf",
                    together_api_key=together_api_key,
                    temperature=settings.temperature
                )
                print("✅ Using Together.ai for LLM")
            except ImportError:
                print("⚠️  langchain-together not installed, falling back to Ollama")
                self.llm = Ollama(
                    model=settings.ollama_model,
                    temperature=settings.temperature,
                    base_url=settings.ollama_base_url,
                )
        else:
            # Fallback to Ollama (local or remote)
            self.llm = Ollama(
                model=settings.ollama_model,
                temperature=settings.temperature,
                base_url=settings.ollama_base_url,
            )
            print(f"✅ Using Ollama ({settings.ollama_model}) for LLM")

    def generate_structured(
        self,
        prompt_template: str,
        schema: Type[BaseModel],
        **prompt_kwargs: Dict[str, Any],
    ) -> BaseModel:
        """Generate structured output enforced by a Pydantic schema."""

        parser = PydanticOutputParser(pydantic_object=schema)
        prompt = PromptTemplate(
            template=prompt_template + "\n{format_instructions}",
            input_variables=list(prompt_kwargs.keys()),
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        formatted = prompt.format(**prompt_kwargs)
        
        try:
            raw_output = self.llm.invoke(formatted)
            
            # Handle different response formats (Gemini, OpenAI, etc.)
            if hasattr(raw_output, 'content'):
                # Gemini returns AIMessage with .content attribute
                text_output = raw_output.content
            elif isinstance(raw_output, str):
                # Direct string response
                text_output = raw_output
            else:
                # Try to convert to string
                text_output = str(raw_output)
            
            try:
                return parser.parse(text_output)
            except OutputParserException:
                repaired = _extract_json_candidate(text_output)
                if not repaired:
                    raise OutputParserException(
                        f"Failed to extract JSON from LLM output. Raw output: {text_output[:200]}..."
                    )
                try:
                    data = json.loads(repaired)
                except json.JSONDecodeError as exc:
                    raise OutputParserException(
                        f"Failed to repair JSON output: {repaired}"
                    ) from exc
                return schema.model_validate(data)
        except Exception as e:
            # Better error handling
            error_msg = f"LLM generation failed: {str(e)}"
            print(f"❌ {error_msg}")
            raise OutputParserException(error_msg) from e


llm_client = LLMClient()
