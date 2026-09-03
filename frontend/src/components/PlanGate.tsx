import React from 'react';
import { Lock, Sparkles, ArrowRight } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';

interface PlanGateProps {
  feature: string;
  requiredPlan: 'pro';
  currentPlan?: string;
  children: React.ReactNode;
  onUpgrade?: () => void;
}

export function PlanGate({
  feature,
  requiredPlan,
  currentPlan = 'free',
  children,
  onUpgrade
}: PlanGateProps) {
  const canAccess = currentPlan === 'pro';

  if (canAccess) {
    return <>{children}</>;
  }

  return (
    <div className="relative">
      <div className="blur-sm opacity-50 pointer-events-none">
        {children}
      </div>

      <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/50 backdrop-blur-sm rounded-lg">
        <div className="text-center p-6 max-w-md">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-gradient-to-br from-violet-500 to-purple-600 rounded-full">
              <Lock className="w-6 h-6 text-white" />
            </div>
          </div>

          <h3 className="text-xl font-bold text-white mb-2">
            {feature} requires a Pro plan
          </h3>

          <p className="text-gray-300 mb-4 text-sm">
            Unlock this feature and more with a Pro subscription — ₹499/month
          </p>

          <div className="flex items-center justify-center gap-2 mb-4">
            <Badge variant="secondary" className="bg-violet-500/20 text-violet-300 border-violet-500/30">
              <Sparkles className="w-3 h-3 mr-1" />
              Pro Feature
            </Badge>
          </div>

          <Button
            onClick={onUpgrade}
            className="bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700"
          >
            Upgrade to Pro
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        </div>
      </div>
    </div>
  );
}
