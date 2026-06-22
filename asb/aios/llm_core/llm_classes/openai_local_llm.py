import os
import re
import time
import json

import openai
from openai import OpenAI

from .base_llm import BaseLLM
from pyopenagi.utils.chat_template import Response


class OpenAILocalLLM(BaseLLM):
    """Backend for a locally served model exposing an OpenAI-compatible API
    (e.g. `vllm serve <model> --port 8000`). Mirrors GPTLLM but points the
    OpenAI client at LOCAL_BASE_URL instead of the OpenAI API.

    Native tool calling is used, so serve the model with tool-call support,
    e.g. `--enable-auto-tool-choice --tool-call-parser hermes` for Qwen.
    """

    def __init__(self, llm_name: str,
                 max_gpu_memory: dict = None,
                 eval_device: str = None,
                 max_new_tokens: int = 1024,
                 log_mode: str = "console"):
        super().__init__(llm_name,
                         max_gpu_memory,
                         eval_device,
                         max_new_tokens,
                         log_mode)

    def load_llm_and_tokenizer(self) -> None:
        self.model = OpenAI(
            api_key=os.getenv("LOCAL_API_KEY", "EMPTY"),
            base_url=os.getenv("LOCAL_BASE_URL", "http://localhost:8000/v1"),
        )
        self.tokenizer = None

    def parse_tool_calls(self, tool_calls):
        if tool_calls:
            parsed_tool_calls = []
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                parsed_tool_calls.append(
                    {
                        "name": function_name,
                        "parameters": function_args
                    }
                )
            return parsed_tool_calls
        return None

    def process(self,
            agent_process,
            temperature=0.0
        ):
        agent_process.set_status("executing")
        agent_process.set_start_time(time.time())
        messages = agent_process.query.messages
        self.logger.log(
            f"{agent_process.agent_name} is switched to executing.\n",
            level = "executing"
        )
        try:
            response = self.model.chat.completions.create(
                model=self.model_name,
                messages = messages,
                tools = agent_process.query.tools,
                max_tokens = self.max_new_tokens,
                seed = 0,
                temperature = temperature,
            )
            response_message = response.choices[0].message.content
            tool_calls = self.parse_tool_calls(
                response.choices[0].message.tool_calls
            )
            agent_process.set_response(
                Response(
                    response_message = response_message,
                    tool_calls = tool_calls
                )
            )
        except openai.APIConnectionError as e:
            agent_process.set_response(
                Response(
                    response_message = f"Server connection error: {e.__cause__}"
                )
            )
        except openai.APIStatusError as e:
            agent_process.set_response(
                Response(
                    response_message = f"Local server STATUS error {e.status_code}: (e.response)"
                )
            )
        except openai.BadRequestError as e:
            agent_process.set_response(
                Response(
                    response_message = f"Local server BAD REQUEST error {e.status_code}: (e.response)"
                )
            )
        except Exception as e:
            agent_process.set_response(
                Response(
                    response_message = f"An unexpected error occurred: {e}"
                )
            )

        agent_process.set_status("done")
        agent_process.set_end_time(time.time())
