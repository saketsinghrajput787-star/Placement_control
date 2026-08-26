import React, { useEffect, useState } from 'react';
import { apiClient } from '../../api/client';
import { Room, Panel } from '../../types';
import { Card } from '../../components/common/Card';
import { Badge } from '../../components/common/Badge';
import { DoorOpen, Users, Video } from 'lucide-react';

export const RoomsPanelsPage: React.FC = () => {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [panels, setPanels] = useState<Panel[]>([]);

  useEffect(() => {
    Promise.all([apiClient.get('/rooms'), apiClient.get('/panels')])
      .then(([roomsRes, panelsRes]) => {
        setRooms(roomsRes.data);
        setPanels(panelsRes.data);
      })
      .catch(console.error);
  }, []);

  return (
    <div className="space-y-6">
      <div className="bg-white p-5 rounded-lg border border-sand-300 shadow-xs">
        <h2 className="text-xl font-bold text-sand-900 tracking-tight">CAMPUS INFRASTRUCTURE: ROOMS & PANELS</h2>
        <p className="text-xs text-sand-600 mt-1">
          Inventory of physical interview rooms across Block A/B and recruiter panel assignments
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Rooms Card */}
        <Card title={`Campus Physical Rooms (${rooms.length})`} subtitle="Block A & Block B interview suites with video conferencing">
          {rooms.length === 0 ? (
            <div className="p-6 text-center text-sand-500 font-semibold text-xs">
              No rooms imported yet. Upload rooms.csv in Data Import Center.
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {rooms.map((r) => (
                <div key={r.id} className="p-3 bg-sand-50 rounded-lg border border-sand-300 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-sm text-forest-800">{r.room_code}</span>
                    {r.has_video_conf && <Video className="w-3.5 h-3.5 text-forest-600" />}
                  </div>
                  <p className="text-sand-600 text-[11px] truncate">{r.building}</p>
                  <Badge variant="healthy" size="sm">
                    Active
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Panels Card */}
        <Card title={`Active Recruiter Panels (${panels.length})`} subtitle="Corporate technical and HR interview boards">
          {panels.length === 0 ? (
            <div className="p-6 text-center text-sand-500 font-semibold text-xs">
              No panels imported yet. Upload panels.csv in Data Import Center.
            </div>
          ) : (
            <div className="divide-y divide-sand-200 max-h-[420px] overflow-y-auto">
              {panels.map((p) => (
                <div key={p.id} className="py-2.5 px-3 flex items-center justify-between hover:bg-sand-50 text-xs">
                  <div>
                    <span className="font-semibold text-sand-900">{p.company_name}</span>
                    <span className="text-sand-500 font-mono ml-2 font-bold text-forest-800">Panel {p.panel_code}</span>
                    <p className="text-[11px] text-sand-500">{p.interviewer_names}</p>
                  </div>
                  <Badge variant="healthy" size="sm">
                    Available
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
