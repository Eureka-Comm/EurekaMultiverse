import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/Card";
import { Database, Table, BarChart2, Search } from "lucide-react";
import { Badge } from "../../components/ui/Badge";

export default function Data() {
  return (
    <div className="flex flex-col h-full p-8 bg-canvas">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-text">Structured Data</h1>
          <p className="text-text-muted mt-1 text-sm">Datasets and relational contexts available for decision evaluation.</p>
        </div>
        <Badge variant="neutral" className="bg-surface border-border">DEMO DATA</Badge>
      </div>

      <div className="flex gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
          <input 
            type="text" 
            placeholder="Search datasets..." 
            className="w-full bg-surface border border-border rounded-md py-2 pl-10 pr-4 text-sm text-text focus:outline-none focus:border-cognitive transition-colors"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {[
          { name: "Historical_Performance_Metrics", rows: 14500, cols: 24, lastUpdated: "2 hrs ago", type: "Time-Series" },
          { name: "Supplier_Reliability_Scores", rows: 320, cols: 8, lastUpdated: "1 day ago", type: "Relational" },
          { name: "Market_Volatility_Index", rows: 5000, cols: 3, lastUpdated: "Just now", type: "Stream" },
        ].map((dataset, i) => (
          <Card key={i} className="bg-surface-elevated border-border hover:border-text-muted transition-colors cursor-pointer">
            <CardContent className="p-6 flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div className="p-3 bg-surface rounded-lg border border-border">
                  <Database className="h-6 w-6 text-scientific" />
                </div>
                <div>
                  <h3 className="font-medium text-text mb-1">{dataset.name}</h3>
                  <div className="flex items-center gap-4 text-xs text-text-muted">
                    <span className="flex items-center gap-1"><Table className="h-3 w-3"/> {dataset.cols} Columns</span>
                    <span className="flex items-center gap-1"><BarChart2 className="h-3 w-3"/> {dataset.rows.toLocaleString()} Rows</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <Badge variant="neutral" className="mb-2 block w-fit ml-auto">{dataset.type}</Badge>
                <span className="text-xs text-text-muted">Updated {dataset.lastUpdated}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}