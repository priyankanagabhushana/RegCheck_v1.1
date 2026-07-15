from compilers.llm_config import get_active_config


def test_active_config_uses_provider_defaults():
    config = get_active_config({"llm_provider": "openai"})

    assert config == {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "api_key": "",
    }


def test_active_config_recovers_from_stale_session_values():
    config = get_active_config({
        "llm_provider": "removed-provider",
        "llm_model": "removed-model",
    })

    assert config["provider"] == "deepseek"
    assert config["model"] == "deepseek/deepseek-chat"


def test_active_config_rejects_model_from_another_provider():
    config = get_active_config({
        "llm_provider": "openai",
        "llm_model": "deepseek/deepseek-chat",
        "api_key_openai": "test-key",
    })

    assert config["model"] == "gpt-4o-mini"
    assert config["api_key"] == "test-key"
