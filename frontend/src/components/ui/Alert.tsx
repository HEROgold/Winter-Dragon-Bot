import React from 'react';
import type { ReactNode } from 'react';

interface AlertProps {
  type: 'success' | 'error' | 'warning' | 'info';
  children: ReactNode;
  onClose?: () => void;
}

export const Alert: React.FC<AlertProps> = ({ type, children, onClose }) => {
  const alertClasses = {
    success: 'alert-success',
    error: 'alert-error',
    warning: 'alert-warning',
    info: 'alert-info',
  };

  return (
    <div className={`alert ${alertClasses[type]} shadow-lg`}>
      <div>
        {children}
      </div>
      {onClose && (
        <div className="flex-none">
          <button className="btn btn-sm btn-ghost" onClick={onClose}>
            ×
          </button>
        </div>
      )}
    </div>
  );
};
