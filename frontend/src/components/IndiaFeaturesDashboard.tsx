import React, { useState } from "react";
import { Calendar, Globe } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getCulturalEventAutomation } from "@/lib/api";

export function IndiaFeaturesDashboard() {
  const [culturalEvents, setCulturalEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const loadRegionalData = async () => {
    setLoading(true);
    try {
      const events = await getCulturalEventAutomation(90).catch(() => ({ cultural_events: [], total_events: 0 }));
      setCulturalEvents(events.cultural_events && events.cultural_events.length > 0 ? events.cultural_events : []);
    } catch (error) {
      console.error("Error loading cultural events:", error);
      setCulturalEvents([]);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    loadRegionalData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Globe className="h-6 w-6 text-orange-500" />
            India-Specific Features
          </h2>
          <p className="text-sm text-muted-foreground">Cultural events and upcoming festivals</p>
        </div>
      </div>

      {/* Cultural Events — sourced from CulturalEventCalendar (static known dates) */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Upcoming Cultural Events
          </CardTitle>
          <CardDescription>Major festivals and events in the next 90 days</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : culturalEvents.length === 0 ? (
            <p className="text-sm text-muted-foreground">No upcoming events in the next 90 days.</p>
          ) : (
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
          )}
        </CardContent>
      </Card>

      {/* Removed: Regional Trends, Timing, Creator Patterns — these were fabricated data.
          The backend endpoints returned hardcoded viral_score=75.0 for every region/city/language.
          Real regional trend tracking will ship when live data sources are available. */}
    </div>
  );
}
