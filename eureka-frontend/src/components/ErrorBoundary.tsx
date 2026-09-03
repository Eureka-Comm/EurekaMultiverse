import React, { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { useWorkStore } from '../store/workStore';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundaryClass extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
    this.setState({
      error,
      errorInfo
    });
  }

  public render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} errorInfo={this.state.errorInfo} />;
    }

    return this.props.children;
  }
}

const ErrorFallback = ({ error, errorInfo }: { error: Error | null, errorInfo: ErrorInfo | null }) => {
  const activeWork = useWorkStore((state) => state.activeWork);
  const clearWork = useWorkStore((state) => state.clearWork);

  return (
    <div className="flex h-screen bg-[var(--eureka-canvas)] items-center justify-center text-[var(--eureka-text-section)]">
      <div className="flex flex-col items-center max-w-3xl space-y-6 text-center">
        <h2 className="text-3xl text-purple-500 font-light">EUREKA WORKSPACE RUNTIME ERROR</h2>
        <div className="fabric-panel p-6 bg-[#16161c] border-purple-500 border w-full text-left overflow-auto">
          <p className="text-sm font-bold mb-4">React UI Crash Detected</p>
          <div className="space-y-2 text-xs text-purple-300 font-mono">
            <p><strong>WORK_ID:</strong> {activeWork?.work?.workId || 'UNKNOWN'}</p>
            <p><strong>REVISION:</strong> {activeWork?.revision || 'UNKNOWN'}</p>
            <p><strong>ERROR:</strong> {error?.message}</p>
          </div>
          {errorInfo && (
            <pre className="mt-4 p-4 bg-black text-[10px] text-gray-500 overflow-x-auto">
              {errorInfo.componentStack}
            </pre>
          )}
        </div>
        <button 
          onClick={() => {
            clearWork();
            window.location.reload();
          }} 
          className="px-6 py-2 bg-[var(--eureka-signal-action)] text-white font-bold rounded text-sm hover:opacity-90"
        >
          RELOAD WORKSPACE
        </button>
      </div>
    </div>
  );
};

export default function ErrorBoundary({ children }: { children: ReactNode }) {
  return <ErrorBoundaryClass>{children}</ErrorBoundaryClass>;
}
