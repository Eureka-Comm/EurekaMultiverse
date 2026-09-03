import React, { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-screen w-full bg-surface text-text-primary p-8">
          <div className="bg-surface-elevated border border-signal-blocked p-6 max-w-3xl w-full">
            <h1 className="text-signal-blocked text-xl font-bold mb-4">Frontend Runtime Error</h1>
            <p className="text-text-muted mb-4 text-sm font-mono">{this.state.error?.message}</p>
            <pre className="text-[10px] text-text-technical overflow-auto p-4 bg-canvas border border-[var(--eureka-spatial-hairline)] max-h-96">
              {this.state.error?.stack}
              {'\n\n'}
              {this.state.errorInfo?.componentStack}
            </pre>
            <button
              className="mt-4 px-4 py-2 border border-signal-cognitive text-signal-cognitive text-xs hover:bg-signal-cognitive hover:text-canvas"
              onClick={() => window.location.reload()}
            >
              RELOAD EUREKA
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
