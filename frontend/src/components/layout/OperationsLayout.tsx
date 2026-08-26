import React from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { ExplainabilityDrawer } from '../schedule/ExplainabilityDrawer';
import { DisruptionSimulatorModal } from '../disruptions/DisruptionSimulatorModal';
import { AICopilotDrawer } from '../copilot/AICopilotDrawer';
import { ScheduleDiffModal } from '../schedule/ScheduleDiffModal';
import { ScheduleVersionHistoryDrawer } from '../schedule/ScheduleVersionHistoryDrawer';

export const OperationsLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-sand-100 flex flex-col text-sand-900">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-6 overflow-y-auto max-w-7xl mx-auto w-full">
          <Outlet />
        </main>
      </div>

      {/* Global Drawers & Modals */}
      <ExplainabilityDrawer />
      <DisruptionSimulatorModal />
      <AICopilotDrawer />
      <ScheduleDiffModal />
      <ScheduleVersionHistoryDrawer />
    </div>
  );
};
