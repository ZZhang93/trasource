import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from google import genai
from google.genai import types

from backend.routes import settings as settings_routes
from core.llm_provider import GeminiProvider


def _response(*parts):
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(content=types.Content(role="model", parts=list(parts)))
        ]
    )


class GeminiProviderTests(unittest.TestCase):
    def _provider(self, client, **kwargs):
        with patch.object(genai, "Client", return_value=client) as client_cls:
            provider = GeminiProvider(
                api_key="test-key",
                model_name="gemini-test",
                **kwargs,
            )
        return provider, client_cls

    def test_client_uses_scoped_proxy_without_mutating_environment(self):
        client = MagicMock()
        with patch.dict(os.environ, {}, clear=True):
            _, client_cls = self._provider(
                client, proxy_url="http://proxy.example:8080"
            )
            self.assertNotIn("HTTPS_PROXY", os.environ)

        call_kwargs = client_cls.call_args.kwargs
        self.assertEqual(call_kwargs["api_key"], "test-key")
        options = call_kwargs["http_options"]
        self.assertEqual(options.client_args["proxy"], "http://proxy.example:8080")
        self.assertEqual(
            options.async_client_args["proxy"], "http://proxy.example:8080"
        )

    def test_generate_passes_config_and_omits_thought_parts(self):
        client = MagicMock()
        client.models.generate_content.return_value = _response(
            types.Part.from_text(text="first"),
            types.Part(thought=True, text="private reasoning"),
            types.Part.from_text(text="second"),
        )
        provider, _ = self._provider(client)

        text = provider.generate(
            "question", system_prompt="system", temperature=0.25, max_tokens=321
        )

        self.assertEqual(text, "first\nsecond")
        call_kwargs = client.models.generate_content.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "gemini-test")
        self.assertEqual(call_kwargs["contents"], "question")
        self.assertEqual(call_kwargs["config"].system_instruction, "system")
        self.assertEqual(call_kwargs["config"].temperature, 0.25)
        self.assertEqual(call_kwargs["config"].max_output_tokens, 321)

    def test_generate_stream_yields_visible_text_chunks(self):
        client = MagicMock()
        client.models.generate_content_stream.return_value = iter([
            types.GenerateContentResponse(),
            _response(types.Part.from_text(text="one")),
            _response(
                types.Part(thought=True, text="hidden"),
                types.Part.from_text(text="two"),
            ),
        ])
        provider, _ = self._provider(client)

        self.assertEqual(list(provider.generate_stream("question")), ["one", "two"])

    def test_chat_stream_maps_assistant_role_to_model(self):
        client = MagicMock()
        client.models.generate_content_stream.return_value = iter([
            _response(types.Part.from_text(text="answer"))
        ])
        provider, _ = self._provider(client)

        output = list(provider.chat_stream(
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
                {"role": "user", "content": "continue"},
            ],
            system_prompt="be concise",
            temperature=0.5,
            max_tokens=123,
        ))

        self.assertEqual(output, ["answer"])
        call_kwargs = client.models.generate_content_stream.call_args.kwargs
        contents = call_kwargs["contents"]
        self.assertEqual([item.role for item in contents], ["user", "model", "user"])
        self.assertEqual([item.parts[0].text for item in contents], ["hello", "hi", "continue"])
        self.assertEqual(call_kwargs["config"].system_instruction, "be concise")


class GeminiModelListingTests(unittest.TestCase):
    def test_list_models_uses_supported_actions_and_saved_proxy(self):
        client = MagicMock()
        client.models.list.return_value = [
            SimpleNamespace(
                name="models/gemini-z", display_name="Gemini Z",
                supported_actions=["generateContent"],
            ),
            SimpleNamespace(
                name="models/embed-only", display_name="Embed",
                supported_actions=["embedContent"],
            ),
            SimpleNamespace(
                name="models/gemini-a", display_name=None,
                supported_actions=["generateContent"],
            ),
        ]

        with (
            patch.object(genai, "Client", return_value=client) as client_cls,
            patch.object(settings_routes, "_resolve_key", return_value="saved-key"),
            patch.object(
                settings_routes,
                "_get_settings",
                return_value={"proxy_url": "http://proxy.example:8080"},
            ),
        ):
            result = settings_routes.list_models(
                settings_routes.ListModelsRequest(provider="gemini")
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["models"], [
            {"label": "Gemini Z", "value": "gemini-z"},
            {"label": "gemini-a", "value": "gemini-a"},
        ])
        options = client_cls.call_args.kwargs["http_options"]
        self.assertEqual(options.client_args["proxy"], "http://proxy.example:8080")
        client.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
