import React, { useState } from "react";
import { Sparkles, Copy, CheckCircle, RefreshCw } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { useQuery } from "@tanstack/react-query";
import { generateCaption, fetchTrends, type ApiCaptionKit } from "@/lib/api";

export function AIContentGenerator() {
  const [activeTab, setActiveTab] = useState("caption");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // Caption generation state
  const [selectedTrendId, setSelectedTrendId] = useState<string>("");
  const [selectedVibe, setSelectedVibe] = useState(0);
  const [generatedCaptionKit, setGeneratedCaptionKit] = useState<ApiCaptionKit | null>(null);

  // Fetch available trends for the selector
  const { data: trends = [] } = useQuery({
    queryKey: ["trends-for-caption"],
    queryFn: () => fetchTrends(),
  });

  const handleGenerateCaption = async () => {
    if (!selectedTrendId) {
      toast.error("Please select a trend");
      return;
    }
    setLoading(true);
    setSelectedVibe(0);
    try {
      const result = await generateCaption(Number(selectedTrendId));
      setGeneratedCaptionKit(result);
      if (result.is_fallback) {
        toast.warning(result.fallback_reason || "Showing template captions — LLM unavailable");
      } else {
        toast.success("Caption kit generated!");
      }
    } catch (error) {
      toast.error("Failed to generate caption");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-purple-500" />
            AI Content Generator
          </h2>
          <p className="text-sm text-muted-foreground">Generate captions, ideas, hooks, and scripts instantly</p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="flex w-full overflow-x-auto justify-start md:justify-center p-1 h-auto no-scrollbar gap-1.5">
          <TabsTrigger value="caption" className="shrink-0">Caption</TabsTrigger>
        </TabsList>

        {/* Caption Generation */}
        <TabsContent value="caption" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Generate Caption Kit</CardTitle>
              <CardDescription>Select a trend to generate 3 AI-powered caption variants, hashtags, and posting strategy</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Select Trend</Label>
                <Select value={selectedTrendId} onValueChange={setSelectedTrendId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose a trending audio..." />
                  </SelectTrigger>
                  <SelectContent>
                    {trends.map((t) => (
                      <SelectItem key={t.id} value={t.id}>
                        {t.song} — {t.artist}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={handleGenerateCaption} disabled={loading || !selectedTrendId} className="w-full">
                {loading ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
                Generate Caption Kit
              </Button>

              {generatedCaptionKit && (
                <div className="space-y-4 pt-4 border-t">
                  {/* Vibe tabs */}
                  {generatedCaptionKit.captions.length > 0 && (
                    <>
                      <div className="flex gap-2">
                        {generatedCaptionKit.captions.map((c, i) => (
                          <button
                            key={i}
                            onClick={() => setSelectedVibe(i)}
                            className={`rounded-full px-3 py-1.5 text-xs font-semibold capitalize transition-all ${
                              selectedVibe === i
                                ? "bg-primary text-white"
                                : "bg-muted text-muted-foreground hover:text-foreground"
                            }`}
                          >
                            {c.vibe}
                          </button>
                        ))}
                      </div>

                      {/* Active caption */}
                      <div className="relative rounded-xl bg-white/[0.03] border border-border p-4">
                        <p className="text-sm leading-relaxed pr-8">{generatedCaptionKit.captions[selectedVibe]?.text}</p>
                        <button
                          onClick={() => copyToClipboard(generatedCaptionKit.captions[selectedVibe]?.text || "")}
                          className="absolute right-3 top-3 text-muted-foreground hover:text-foreground"
                        >
                          {copied ? <CheckCircle className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
                        </button>
                      </div>
                    </>
                  )}

                  {/* Hashtags */}
                  {generatedCaptionKit.hashtags.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {generatedCaptionKit.hashtags.map((tag, i) => (
                        <Badge key={i} variant="secondary">#{tag.replace(/^#/, "")}</Badge>
                      ))}
                    </div>
                  )}

                  {/* Audio cue */}
                  {generatedCaptionKit.audio_cue && (
                    <div className="text-sm text-muted-foreground">
                      <span className="font-medium">Audio cue:</span> {generatedCaptionKit.audio_cue}
                    </div>
                  )}

                  {/* Posting strategy */}
                  {generatedCaptionKit.posting_strategy && (
                    <div className="text-sm text-muted-foreground">
                      <span className="font-medium">Best time:</span> {generatedCaptionKit.posting_strategy.best_hour_ist}:00 IST on {generatedCaptionKit.posting_strategy.best_days.join(", ")}
                    </div>
                  )}

                  {generatedCaptionKit.is_fallback && (
                    <Badge variant="outline" className="text-xs">Template captions — LLM unavailable</Badge>
                  )}
                  {generatedCaptionKit.is_partial && (
                    <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-1.5 text-amber-400 text-xs font-medium">
                      Some strategy fields unavailable for this trend: {generatedCaptionKit.missing_fields?.join(", ")}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}