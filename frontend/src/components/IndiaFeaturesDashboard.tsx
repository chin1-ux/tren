import React, { useState } from "react";
import { MapPin, Calendar, Globe, Languages, Clock, TrendingUp, Sparkles } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getRegionalTrends, getRegionalTimingOptimization, getCulturalEventAutomation, getCreatorPatternAnalysis } from "@/lib/api";

export function IndiaFeaturesDashboard() {
  const [selectedRegion, setSelectedRegion] = useState("north");
  const [regionalTrends, setRegionalTrends] = useState<any[]>([]);
  const [timing, setTiming] = useState<any>(null);
  const [culturalEvents, setCulturalEvents] = useState<any[]>([]);
  const [creatorPatterns, setCreatorPatterns] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadRegionalData = async () => {
    setLoading(true);
    try {
      const [trends, timingData, events, patterns] = await Promise.all([
        getRegionalTrends(selectedRegion),
        getRegionalTimingOptimization(selectedRegion),
        getCulturalEventAutomation(90),
        getCreatorPatternAnalysis(selectedRegion)
      ]);
      setRegionalTrends(trends.regional_trends);
      setTiming(timingData);
      setCulturalEvents(events.cultural_events);
      setCreatorPatterns(patterns);
    } catch (error) {
      console.error("Error loading regional data:", error);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    loadRegionalData();
  }, [selectedRegion]);

  const regions = [
    { value: "north", label: "North India", cities: ["Delhi", "Mumbai", "Jaipur"] },
    { value: "south", label: "South India", cities: ["Chennai", "Bangalore", "Hyderabad"] },
    { value: "east", label: "East India", cities: ["Kolkata", "Bhubaneswar", "Guwahati"] },
    { value: "west", label: "West India", cities: ["Mumbai", "Pune", "Ahmedabad"] },
    { value: "central", label: "Central India", cities: ["Bhopal", "Indore", "Nagpur"] }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Globe className="h-6 w-6 text-orange-500" />
            India-Specific Features
          </h2>
          <p className="text-sm text-muted-foreground">Regional trends, cultural events, and timing optimization</p>
        </div>
        <Select value={selectedRegion} onValueChange={setSelectedRegion}>
          <SelectTrigger className="w-[200px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {regions.map((region) => (
              <SelectItem key={region.value} value={region.value}>
                {region.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Regional Timing */}
      {timing && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Regional Timing Optimization
            </CardTitle>
            <CardDescription>Optimal posting times for {timing.city}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium mb-2">Peak Hours (IST)</p>
                <div className="flex flex-wrap gap-2">
                  {timing.peak_hours.map((hour: number) => (
                    <Badge key={hour} variant="secondary">
                      {hour}:00
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm font-medium mb-2">Best Days</p>
                <div className="flex flex-wrap gap-2">
                  {timing.best_days.map((day: string) => (
                    <Badge key={day} variant="outline">
                      {day}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-4 pt-4 border-t">
              <p className="text-xs text-muted-foreground">
                Timezone: {timing.timezone_offset}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Regional Trends */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            Regional Trends
          </CardTitle>
          <CardDescription>Trending content in your selected region</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {regionalTrends.slice(0, 5).map((trend, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                <div>
                  <p className="font-medium">{trend.city} - {trend.language}</p>
                  <p className="text-sm text-muted-foreground">{trend.trend_name}</p>
                </div>
                <Badge variant="outline">
                  {trend.viral_score.toFixed(0)}/100
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Cultural Events */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Upcoming Cultural Events
          </CardTitle>
          <CardDescription>Major festivals and events in the next 90 days</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {culturalEvents.map((event, i) => (
              <div key={i} className="p-4 border rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold">{event.event_name}</h4>
                  <Badge variant="secondary">
                    {new Date(event.event_date).toLocaleDateString()}
                  </Badge>
                </div>
                <div className="flex flex-wrap gap-2 mb-2">
                  {event.content_automation.slice(0, 3).map((idea: string, j: number) => (
                    <Badge key={j} variant="outline" className="text-xs">
                      {idea}
                    </Badge>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  {event.creator_opportunities[0]}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Creator Patterns */}
      {creatorPatterns && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Creator Pattern Analysis
            </CardTitle>
            <CardDescription>Success factors for creators in this region</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <p className="text-sm font-medium mb-2">Popular Languages</p>
                <div className="flex flex-wrap gap-2">
                  {creatorPatterns.popular_languages.map((lang: string) => (
                    <Badge key={lang} variant="secondary">
                      {lang}
                    </Badge>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm font-medium mb-2">Cultural Themes</p>
                <div className="flex flex-wrap gap-2">
                  {creatorPatterns.cultural_themes.map((theme: string) => (
                    <Badge key={theme} variant="outline">
                      {theme}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="pt-4 border-t">
                <p className="text-sm font-medium mb-2">Success Factors</p>
                <ul className="space-y-1">
                  {creatorPatterns.success_factors.map((factor: string, i: number) => (
                    <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                      <Sparkles className="h-3 w-3 mt-0.5 text-emerald-500" />
                      {factor}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}