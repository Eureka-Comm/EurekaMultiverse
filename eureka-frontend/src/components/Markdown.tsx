import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Renderiza markdown (GFM: tablas, negritas, headers, listas, código) como el
 * DeepSeek Harness, con la paleta clara de EUREKA.
 */
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="md-content text-sm text-[var(--eureka-text-section)] leading-relaxed">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
