import React from 'react';
import UniversalIntake from './UniversalIntake';
import DynamicWorkspace from './DynamicWorkspace';
import ContractErrorState from './ContractErrorState';
import RuntimeErrorState from './RuntimeErrorState';
import ErrorBoundary from '../components/ErrorBoundary';
import EurekaSidebar from '../components/layout/EurekaSidebar';
import { useWorkStore } from '../store/workStore';

export default function UniversalRoot() {
  const appState = useWorkStore((state) => state.appState);

  const renderContent = () => {
    switch (appState) {
      case 'BOOTING':
        return (
          <div className="flex h-screen bg-[var(--eureka-canvas)] items-center justify-center">
            <div className="text-[var(--eureka-text-label)] animate-pulse">EUREKA BOOTING...</div>
          </div>
        );
      case 'READY':
        return <DynamicWorkspace />;
      case 'CONTRACT_ERROR':
        return <ContractErrorState />;
      case 'RUNTIME_ERROR':
        return <RuntimeErrorState />;
      case 'NO_WORK':
      default:
        return <UniversalIntake />;
    }
  };

  return (
    <ErrorBoundary>
      <div className="flex h-screen overflow-hidden">
        <EurekaSidebar />
        <div className="flex-1 min-w-0 flex flex-col overflow-hidden">{renderContent()}</div>
      </div>
    </ErrorBoundary>
  );
}

