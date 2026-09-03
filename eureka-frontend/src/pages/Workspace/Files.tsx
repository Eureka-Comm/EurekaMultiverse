import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { FileText, File, UploadCloud, Search } from "lucide-react";
import { Badge } from "../../components/ui/Badge";

export default function Files() {
  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Knowledge Files</h1>
          <p className="text-text-muted mt-1 text-sm">Unstructured documents injected into the cognitive context.</p>
        </div>
        <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
      </div>

      <div className="flex gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
          <input 
            type="text" 
            placeholder="Search documents..." 
            className="w-full bg-surface border border-border rounded-md py-2 pl-10 pr-4 text-sm text-text focus:outline-none focus:border-cognitive transition-colors"
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-surface-elevated border border-border rounded-md text-sm text-text hover:bg-surface-elevated/80 transition-colors">
          <UploadCloud className="h-4 w-4" /> Upload Document
        </button>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {[
          { name: "Compliance_Policy_2026.pdf", type: "PDF", size: "2.4 MB", status: "Indexed" },
          { name: "Supplier_Contracts_Q3.docx", type: "DOCX", size: "1.1 MB", status: "Indexed" },
          { name: "Risk_Assessment_Matrix.md", type: "Markdown", size: "45 KB", status: "Indexed" },
          { name: "Meeting_Transcript_Arch.txt", type: "Text", size: "120 KB", status: "Parsing..." },
        ].map((file, i) => (
          <Card key={i} className="bg-surface-elevated border-border hover:border-text-muted transition-colors cursor-pointer">
            <CardContent className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="p-3 bg-surface rounded-lg border border-border">
                  <FileText className="h-6 w-6 text-cognitive" />
                </div>
                <Badge variant={file.status === "Indexed" ? "scientific" : "neutral"}>{file.status}</Badge>
              </div>
              <h3 className="font-medium text-text mb-1 truncate" title={file.name}>{file.name}</h3>
              <div className="flex items-center justify-between text-xs text-text-muted">
                <span>{file.type}</span>
                <span>{file.size}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}