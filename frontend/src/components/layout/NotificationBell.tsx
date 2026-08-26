import React, { useState } from 'react';
import { useOperations } from '../../store/operationsStore';

export const NotificationBell: React.FC = () => {
  const { notifications, markNotificationAsRead } = useOperations();
  const [isOpen, setIsOpen] = useState(false);

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-xl text-sand-700 hover:bg-sand-200/80 transition-colors focus:outline-hidden"
        title="Notifications"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-amber-600 text-[10px] font-bold text-white shadow-xs">
            {unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-white border border-sand-300 shadow-xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
          <div className="p-3 bg-sand-100 border-b border-sand-200 flex items-center justify-between">
            <h4 className="text-sm font-bold text-sand-900 flex items-center gap-2">
              <span>Live Notifications</span>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 rounded-full text-xs bg-amber-100 text-amber-800 font-semibold">
                  {unreadCount} new
                </span>
              )}
            </h4>
            <button
              onClick={() => setIsOpen(false)}
              className="text-xs text-sand-500 hover:text-sand-800"
            >
              Close
            </button>
          </div>

          <div className="max-h-80 overflow-y-auto divide-y divide-sand-100">
            {notifications.length === 0 ? (
              <div className="p-6 text-center text-xs text-sand-500">
                No notifications yet.
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  onClick={() => markNotificationAsRead(n.id)}
                  className={`p-3.5 hover:bg-sand-50 transition-colors cursor-pointer ${
                    !n.is_read ? 'bg-amber-50/40' : ''
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <h5 className="text-xs font-bold text-sand-900">{n.title}</h5>
                    <span className="text-[10px] text-sand-400">
                      {n.created_at ? new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                    </span>
                  </div>
                  <p className="text-xs text-sand-600 mt-1 leading-relaxed">{n.message}</p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
