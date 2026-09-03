import * as fs from 'fs';
import * as path from 'path';

const pages = [
  'Overview',
  'Cases/CasesList',
  'Cases/CaseDetail',
  'Cognitive/Chat',
  'Cognitive/Sandbox',
  'Workspace/Files',
  'Workspace/Data',
  'Analytics/Dashboard',
  'Analytics/Explorer',
  'Analytics/Scenarios',
  'Analytics/Networks',
  'Decision/Objective',
  'Decision/Predicate',
  'Decision/Evaluations',
  'Decision/Ranking',
  'Decision/Selection',
  'Decision/Prescription',
  'Governance/Authority',
  'Governance/Freezer',
  'Governance/Unfreezer',
  'Governance/Actioner',
  'Story/Executive',
  'Story/Technical',
  'Story/Timeline',
  'System/Agents',
  'System/Runtime',
  'System/Audit',
  'System/Settings'
];

const basePath = path.join(process.cwd(), 'src', 'pages');

pages.forEach(p => {
  const fullPath = path.join(basePath, p + '.tsx');
  const dir = path.dirname(fullPath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  
  const componentName = p.split('/').pop();
  const content = `export default function ${componentName}() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">${componentName}</h1>
      <p className="text-text-muted">This is the ${componentName} view.</p>
    </div>
  );
}`;
  fs.writeFileSync(fullPath, content);
});
console.log('Pages generated.');
