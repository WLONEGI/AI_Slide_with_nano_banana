"use client";
import { useState } from 'react';
import LandingPage from '@/components/LandingPage';
import Workspace from '@/components/Workspace';

export default function Home() {
  const [initialMessage, setInitialMessage] = useState<string>("");
  const [hasStarted, setHasStarted] = useState(false);

  const handleStart = (message: string) => {
    setInitialMessage(message);
    setHasStarted(true);
  };

  if (!hasStarted) {
    return <LandingPage onStart={handleStart} />;
  }

  return <Workspace initialMessage={initialMessage} />;
}
