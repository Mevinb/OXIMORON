from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()

def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "OXIMORON: Local-first AI orchestration CLI" in result.output
    assert "status" in result.output
    assert "models" in result.output
    assert "engines" in result.output
    assert "ask" in result.output
    assert "generate" in result.output
    assert "logs" in result.output

def test_cli_status_mocked():
    with patch("apps.cli.main.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.get.return_value = {
            "status": "ok",
            "supervisor_id": "test-sup-123",
            "cpu_percent": 14.5,
            "ram_used_gb": 8.2,
            "ram_total_gb": 16.0,
            "gpu_available": True,
            "active_engines": 1,
            "active_jobs": 0,
        }
        mock_get_client.return_value = mock_client

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "OXIMORON Status Summary" in result.output
        assert "test-sup-123" in result.output
        assert "14.5%" in result.output

def test_cli_models_mocked():
    with patch("apps.cli.main.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.get.return_value = [
            {
                "name": "flux1-dev-Q3_K_S.gguf",
                "role": "image_checkpoint",
                "format": "gguf",
                "locations": [{"display_path": "/home/mevlec/Data/models/flux.gguf"}],
            }
        ]
        mock_get_client.return_value = mock_client

        result = runner.invoke(app, ["models"])
        assert result.exit_code == 0
        assert "Registered Model Library" in result.output
        assert "flux1-dev-Q3_K_S.gguf" in result.output

def test_cli_engines_mocked():
    with patch("apps.cli.main.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.get.return_value = [
            {
                "id": "eng-llama-123456",
                "display_name": "llama.cpp Local Server",
                "adapter_key": "llamacpp",
                "observed_state": "RUNNING",
                "endpoint": "http://127.0.0.1:8080",
            }
        ]
        mock_get_client.return_value = mock_client

        result = runner.invoke(app, ["engines"])
        assert result.exit_code == 0
        assert "Configured Inference Engines" in result.output
        assert "llama.cpp" in result.output
        assert "RUNNING" in result.output

        # Also test --json flag
        res_json = runner.invoke(app, ["engines", "--json"])
        assert res_json.exit_code == 0
        assert "llama.cpp Local Server" in res_json.output
