import React, { useState } from "react";
import { Sparkles, Lightbulb, Wand2, Clock, Copy, CheckCircle, RefreshCw } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { generateCaption, generateContentIdeas, generateAIHooks, generateScriptOutline } from "@/lib/api";

export function AIContentGenerator() {
  const [activeTab, setActiveTab] = useState("caption");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // Caption generation state
  const [trendName, setTrendName] = useState("");
  const [captionTone, setCaptionTone] = useState("casual");
  const [captionNiche, setCaptionNiche] = useState("general");
  const [generatedCaption, setGeneratedCaption] = useState<any>(null);

  // Content ideas state
  const [ideasNiche, setIdeasNiche] = useState("fitness");
  const [ideasCount, setIdeasCount] = useState(5);
  const [generatedIdeas, setGeneratedIdeas] = useState<any[]>([]);

  // Hooks generation state
  const [hookTopic, setHookTopic] = useState("");
  const [hooksCount, setHooksCount] = useState(5);
  const [generatedHooks, setGeneratedHooks] = useState<any[]>([]);

  // Script outline state
  const [scriptTopic, setScriptTopic] = useState("");
  const [scriptContentType, setScriptContentType] = useState("reel");
  const [scriptDuration, setScriptDuration] = useState(30);
  const [generatedScript, setGeneratedScript] = useState<any>(null);

  const handleGenerateCaption = async () => {
    if (!trendName.trim()) {
      toast.error("Please enter a trend name");
      return;
    }
    setLoading(true);
    try {
      const result = await generateCaption(trendName, captionTone, captionNiche);
      setGeneratedCaption(result);
      toast.success("Caption generated!");
    } catch (error) {
      toast.error("Failed to generate caption");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateIdeas = async () => {
    setLoading(true);
    try {
      const result = await generateContentIdeas(ideasNiche, ideasCount);
      setGeneratedIdeas(result.content_ideas);
      toast.success(`${result.total_ideas} content ideas generated!`);
    } catch (error) {
      toast.error("Failed to generate content ideas");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateHooks = async () => {
    if (!hookTopic.trim()) {
      toast.error("Please enter a topic");
      return;
    }
    setLoading(true);
    try {
      const result = await generateAIHooks(hookTopic, hooksCount);
      setGeneratedHooks(result.hooks);
      toast.success(`${result.total_hooks} hooks generated!`);
    } catch (error) {
      toast.error("Failed to generate hooks");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateScript = async () => {
    if (!scriptTopic.trim()) {
      toast.error("Please enter a topic");
      return;
    }
    setLoading(true);
    try {
      const result = await generateScriptOutline(scriptContentType, scriptTopic, scriptDuration);
      setGeneratedScript(result);
      toast.success("Script outline generated!");
    } catch (error) {
      toast.error("Failed to generate script outline");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success("Copied to clipboard!");
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
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="caption">Caption</TabsTrigger>
          <TabsTrigger value="ideas">Content Ideas</TabsTrigger>
          <TabsTrigger value="hooks">Hooks</TabsTrigger>
          <TabsTrigger value="script">Script</TabsTrigger>
        </TabsList>

        {/* Caption Generation */}
        <TabsContent value="caption" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Generate Caption</CardTitle>
              <CardDescription>Create engaging captions for your content</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Trend Name</Label>
                <Input
                  placeholder="e.g., Dance Challenge, Morning Routine"
                  value={trendName}
                  onChange={(e) => setTrendName(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Tone</Label>
                  <Select value={captionTone} onValueChange={setCaptionTone}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="casual">Casual</SelectItem>
                      <SelectItem value="professional">Professional</SelectItem>
                      <SelectItem value="funny">Funny</SelectItem>
                      <SelectItem value="inspiring">Inspiring</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Niche</Label>
                  <Select value={captionNiche} onValueChange={setCaptionNiche}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="general">General</SelectItem>
                      <SelectItem value="fitness">Fitness</SelectItem>
                      <SelectItem value="food">Food</SelectItem>
                      <SelectItem value="comedy">Comedy</SelectItem>
                      <SelectItem value="fashion">Fashion</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Button onClick={handleGenerateCaption} disabled={loading} className="w-full">
                {loading ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Wand2 className="h-4 w-4 mr-2" />}
                Generate Caption
              </Button>

              {generatedCaption && (
                <div className="space-y-3 pt-4 border-t">
                  <div className="flex items-center justify-between">
                    <Label>Generated Caption</Label>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(generatedCaption.caption)}
                    >
                      {copied ? <CheckCircle className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    </Button>
                  </div>
                  <Textarea
                    value={generatedCaption.caption}
                    readOnly
                    className="min-h-[100px]"
                  />
                  <div className="flex flex-wrap gap-2">
                    {generatedCaption.hashtags.map((tag: string, i: number) => (
                      <Badge key={i} variant="secondary">{tag}</Badge>
                    ))}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <span className="font-medium">CTA:</span> {generatedCaption.cta}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Content Ideas */}
        <TabsContent value="ideas" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Generate Content Ideas</CardTitle>
              <CardDescription>Get fresh content ideas for your niche</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Niche</Label>
                  <Select value={ideasNiche} onValueChange={setIdeasNiche}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fitness">Fitness</SelectItem>
                      <SelectItem value="food">Food</SelectItem>
                      <SelectItem value="comedy">Comedy</SelectItem>
                      <SelectItem value="fashion">Fashion</SelectItem>
                      <SelectItem value="travel">Travel</SelectItem>
                      <SelectItem value="beauty">Beauty</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Count</Label>
                  <Select value={ideasCount.toString()} onValueChange={(v) => setIdeasCount(parseInt(v))}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="3">3 ideas</SelectItem>
                      <SelectItem value="5">5 ideas</SelectItem>
                      <SelectItem value="10">10 ideas</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Button onClick={handleGenerateIdeas} disabled={loading} className="w-full">
                {loading ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Lightbulb className="h-4 w-4 mr-2" />}
                Generate Ideas
              </Button>

              {generatedIdeas.length > 0 && (
                <div className="space-y-3 pt-4 border-t">
                  <Label>Content Ideas</Label>
                  {generatedIdeas.map((idea, i) => (
                    <Card key={i} className="p-4">
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-semibold">{idea.title}</h4>
                        <Badge variant={idea.difficulty === "easy" ? "default" : "secondary"}>
                          {idea.difficulty}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">{idea.description}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>Type: {idea.content_type}</span>
                        <span>•</span>
                        <span>Engagement: {idea.estimated_engagement}</span>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Hooks */}
        <TabsContent value="hooks" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Generate Hooks</CardTitle>
              <CardDescription>Create attention-grabbing hooks for your content</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Topic</Label>
                  <Input
                    placeholder="e.g., Workout Routine, Healthy Eating"
                    value={hookTopic}
                    onChange={(e) => setHookTopic(e.target.value)}
                  />
                </div>
                <div>
                  <Label>Count</Label>
                  <Select value={hooksCount.toString()} onValueChange={(v) => setHooksCount(parseInt(v))}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="3">3 hooks</SelectItem>
                      <SelectItem value="5">5 hooks</SelectItem>
                      <SelectItem value="10">10 hooks</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Button onClick={handleGenerateHooks} disabled={loading} className="w-full">
                {loading ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Wand2 className="h-4 w-4 mr-2" />}
                Generate Hooks
              </Button>

              {generatedHooks.length > 0 && (
                <div className="space-y-3 pt-4 border-t">
                  <Label>Generated Hooks</Label>
                  {generatedHooks.map((hook, i) => (
                    <Card key={i} className="p-4">
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-xs font-medium uppercase bg-primary/10 px-2 py-1 rounded">
                          {hook.hook_type}
                        </span>
                        <Badge variant="outline">
                          {hook.estimated_retention}% retention
                        </Badge>
                      </div>
                      <p className="font-medium mb-2">{hook.hook_text}</p>
                      <div className="text-xs text-muted-foreground">
                        Best for: {hook.best_for_content.join(", ")}
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Script Outline */}
        <TabsContent value="script" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Generate Script Outline</CardTitle>
              <CardDescription>Create structured scripts for your content</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Topic</Label>
                <Input
                  placeholder="e.g., Morning Routine, Recipe Tutorial"
                  value={scriptTopic}
                  onChange={(e) => setScriptTopic(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Content Type</Label>
                  <Select value={scriptContentType} onValueChange={setScriptContentType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="reel">Reel</SelectItem>
                      <SelectItem value="story">Story</SelectItem>
                      <SelectItem value="post">Post</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Duration (seconds)</Label>
                  <Select value={scriptDuration.toString()} onValueChange={(v) => setScriptDuration(parseInt(v))}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="15">15 seconds</SelectItem>
                      <SelectItem value="30">30 seconds</SelectItem>
                      <SelectItem value="60">60 seconds</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Button onClick={handleGenerateScript} disabled={loading} className="w-full">
                {loading ? <RefreshCw className="h-4 w-4 mr-2 animate-spin" /> : <Wand2 className="h-4 w-4 mr-2" />}
                Generate Script
              </Button>

              {generatedScript && (
                <div className="space-y-3 pt-4 border-t">
                  <Label>Script Outline ({scriptDuration}s)</Label>
                  <div className="space-y-2">
                    {generatedScript.script_outline.map((line: string, i: number) => (
                      <div key={i} className="flex items-start gap-2 text-sm">
                        <span className="text-muted-foreground font-mono">{i + 1}.</span>
                        <span>{line}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}