import React from "react";
import { AudioIdentityCard } from "./AudioIdentityCard";

interface TrendCardVideoProps {
  reel: {
    id: string;
    audio_title?: string | null;
    audio_artist?: string | null;
    audio_use_count?: number | null;
    audio_id?: string | null;
  };
  trendId?: string | number | null;
  opportunityScore?: number;
}

export const TrendCardVideo = ({ reel, trendId, opportunityScore = 50 }: TrendCardVideoProps) => {
  return (
    <AudioIdentityCard
      audioId={reel.audio_id}
      audioTitle={reel.audio_title}
      audioArtist={reel.audio_artist}
      audioUseCount={reel.audio_use_count}
      trendId={trendId}
      opportunityScore={opportunityScore}
    />
  );
};
