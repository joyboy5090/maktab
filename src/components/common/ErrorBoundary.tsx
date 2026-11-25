'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error in component:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="p-8 m-6 bg-rose-50/70 border border-rose-200 rounded-2xl flex flex-col items-center text-center">
          <div className="w-12 h-12 rounded-2xl bg-rose-100 text-rose-600 flex items-center justify-center mb-4">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-gray-900 mb-1">
            Kutilmagan xatolik yuz berdi
          </h3>
          <p className="text-xs text-gray-600 max-w-md mb-4 leading-relaxed">
            {this.state.error?.message || "Sahifa elementlarini yuklashda texnik muammo paydo bo'ldi."}
          </p>
          <button
            onClick={this.handleReset}
            className="flex items-center gap-2 px-4 py-2 bg-[#1E40AF] text-white rounded-xl text-xs font-semibold hover:bg-blue-800 transition shadow-sm"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Sahifani yangilash</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
