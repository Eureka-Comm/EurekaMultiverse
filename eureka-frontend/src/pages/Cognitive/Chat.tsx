import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { Card, CardContent } from "../../components/ui/Card";
import { FileUp, Database, Link, Terminal, Send } from "lucide-react";
import { useNavigate } from "react-router-dom";
import GalaxyConstellation from "../../components/cognitive/GalaxyConstellation";

export default function Chat() {
  const [input, setInput] = useState("");
  const navigate = useNavigate();

  const handleAsk = () => {
    if (input) navigate("/sandbox");
  };

  return (
    <div className="flex h-full flex-col p-6">
      {/* Cerebro / galaxia hero (estilo reel DaCFIiEMPEn) */}
      <div className="mb-6 w-full overflow-hidden rounded-2xl border border-[var(--eureka-spatial-hairline)] shadow-[0_0_60px_-20px_rgba(155,107,255,0.5)]" style={{ height: 'min(34vh, 320px)' }}>
        <GalaxyConstellation />
      </div>

      <div className="flex flex-1 flex-col items-center justify-center">
      <div className="mb-12 text-center">
        <h1 className="text-4xl font-semibold mb-3 tracking-tight">Good morning.</h1>
        <p className="text-lg text-text-muted">What decision are you working on?</p>
      </div>

      <Card className="w-full max-w-3xl overflow-hidden bg-surface-elevated/40 shadow-2xl border-white/10 transition-all focus-within:border-cognitive/50 focus-within:ring-1 focus-within:ring-cognitive/50">
        <CardContent className="p-0">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe a problem, ask a question, upload evidence or explore a decision..."
            className="h-36 w-full resize-none bg-transparent p-6 outline-none text-text-primary placeholder:text-text-muted/50 text-lg leading-relaxed"
          />
          <div className="flex items-center justify-between border-t border-white/5 p-3 bg-surface-elevated/80">
            <div className="flex gap-1">
              <Button variant="ghost" size="sm" className="text-text-muted hover:text-text-primary gap-2">
                <FileUp className="h-4 w-4" /> File
              </Button>
              <Button variant="ghost" size="sm" className="text-text-muted hover:text-text-primary gap-2">
                <Database className="h-4 w-4" /> Data
              </Button>
              <Button variant="ghost" size="sm" className="text-text-muted hover:text-text-primary gap-2">
                <Link className="h-4 w-4" /> Context
              </Button>
              <Button variant="ghost" size="sm" className="text-text-muted hover:text-text-primary gap-2">
                <Terminal className="h-4 w-4" /> Command
              </Button>
            </div>
            <Button variant="primary" onClick={handleAsk} disabled={!input} className="shadow-lg shadow-cognitive/20">
              Ask Eureka <Send className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
      
      <div className="mt-12 flex gap-4">
        <Button variant="outline" onClick={() => navigate("/cases/new")} className="border-white/10">New Decision</Button>
        <Button variant="outline" onClick={() => navigate("/cases")} className="border-white/10">Open Case</Button>
        <Button variant="outline" onClick={() => navigate("/data")} className="border-white/10">Explore Data</Button>
      </div>
      </div>
    </div>
  );
}