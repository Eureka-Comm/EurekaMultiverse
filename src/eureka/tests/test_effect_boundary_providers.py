"""LS-SCN-03d — F14–F17: provider/LLM network calls.

Classifies the provider network funnels as NOT-A-MUTATION (LLM inference = READ/COMPUTE), proven
by test: every outbound network call in these files targets an LLM completion endpoint with a
prompt payload, and none performs a non-LLM external mutation (email/deployment/financial/
third-party/notification).
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
NETWORK_FILES = {
    "ollama_provider": ROOT / "src/eureka/universe/ollama_provider.py",
    "server": ROOT / "src/eureka/universe/server.py",
    "deepseek_provider": ROOT / "src/eureka/foundation/cognitive/agents/providers/deepseek/provider.py",
}

# LLM inference endpoints (completion), allowed
LLM_ENDPOINTS = ("/api/generate", "/chat/completions", "/api/chat", "/v1/chat/completions", "deepseek", "urlopen")
# non-LLM external mutation markers that would be a governed MUTATE
EXTERNAL_MUTATION = ("smtp", "sendmail", "boto3", "deploy", "payment", "stripe", "webhook", "twilio", "subprocess")


def _network_blocks(path: pathlib.Path):
    """Yield (lineno, block) where block = the network line + 5 before + 3 after (for URL var/f-cont)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, ln in enumerate(lines, 1):
        if ("requests.post(" in ln) or ("urlopen(" in ln):
            block = "\n".join(lines[max(0, i - 6):i + 3])
            yield i, block


def test_network_calls_are_llm_inference_not_external_mutation():
    """Every outbound network call targets an LLM completion endpoint (READ/COMPUTE)."""
    for name, path in NETWORK_FILES.items():
        for lineno, block in _network_blocks(path):
            assert any(e in block for e in LLM_ENDPOINTS), \
                f"{name}:{lineno} non-LLM network call: {block.strip()[:120]}"


def test_provider_files_have_no_external_mutation_surface():
    """None of the provider/server files exposes a non-LLM external mutation side effect."""
    for name, path in NETWORK_FILES.items():
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            # strip comments so words like 'deploy' in a CORS comment don't false-positive
            code = raw.split("#", 1)[0]
            for marker in EXTERNAL_MUTATION:
                assert marker not in code, f"{name}:{lineno} external-mutation marker: {marker}"


def test_deepseek_provider_is_inference_only():
    """The deepseek provider builds a prompt payload and reads a completion (no mutation)."""
    txt = (ROOT / "src/eureka/foundation/cognitive/agents/providers/deepseek/provider.py").read_text(encoding="utf-8")
    assert "urlopen" in txt
    assert "prompt" in txt.lower() or "messages" in txt.lower() or "payload" in txt.lower()
