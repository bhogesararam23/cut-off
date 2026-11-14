import { Component, type ReactNode } from 'react';
import { C } from '../lib/content.ts';

/** If a part of the page crashes, show a short message there and keep the rest of the app working. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <p role="alert" className="flex h-full items-center justify-center bg-slate-800 p-4 text-center text-sm text-white">
          {C.errors.map}
        </p>
      );
    }
    return this.props.children;
  }
}
