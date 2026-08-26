import React, { useState, Suspense } from "react";
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { TrendingUp, TrendingDown, Minus, Clock, Users, Video, Heart, MessageCircle, Share2, Award, AlertCircle, CheckCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useUserStore } from "@/store/useAppStore";
import { getCreatorMetrics, getSuccessRecommendations, getContentPerformanceOverTime } from "@/lib/api";

interface CreatorAnalyticsDashboardProps {
  creatorEmail: string;
}

export function CreatorAnalyticsDashboard({ creatorEmail }: CreatorAnalyticsDashboardProps) {
  const [metrics, setMetrics] = useState<any>(null);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [performanceData, setPerformanceData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const userPlan = useUserStore((s) => s.plan) || "free";

  React.useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        if (userPlan === "free") {
          setLoading(false);
          return;
        }
        const [metricsData, recsData, perfData] = await Promise.all([
          getCreatorMetrics(30).catch(() => null),
          getSuccessRecommendations().catch(() => ({ recommendations: [], total_recommendations: 0 })),
          getContentPerformanceOverTime(30).catch(() => ({ performance_data: [], days_analyzed: 0 }))
        ]);
        setMetrics(metricsData);
        setRecommendations(recsData.recommendations);
        setPerformanceData(perfData?.performance_data || []);
      } catch (error) {
        console.error("Error loading analytics:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [creatorEmail]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-2">
                <div className="h-4 bg-muted rounded w-1/2" />
              </CardHeader>
              <CardContent>
                <div className="h-8 bg-muted rounded w-3/4" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-center text-muted-foreground">Unable to load analytics data</p>
        </CardContent>
      </Card>
    );
  }

  // Instagram OAuth not available in beta — show analytics with whatever data exists
  // instead of blocking with a "Coming Soon" dead-end

  const getGrowthIcon = (trend: string) => {
    if (trend === "growing") return <TrendingUp className="h-4 w-4 text-emerald-500" />;
    if (trend === "declining") return <TrendingDown className="h-4 w-4 text-rose-500" />;
    return <Minus className="h-4 w-4 text-amber-500" />;
  };

  const getGrowthColor = (trend: string) => {
    if (trend === "growing") return "text-emerald-500";
    if (trend === "declining") return "text-rose-500";
    return "text-amber-500";
  };

  const getRecommendationIcon = (type: string) => {
    if (type === "critical") return <AlertCircle className="h-4 w-4 text-rose-500" />;
    if (type === "warning") return <AlertCircle className="h-4 w-4 text-amber-500" />;
    if (type === "success") return <CheckCircle className="h-4 w-4 text-emerald-500" />;
    return <CheckCircle className="h-4 w-4 text-blue-500" />;
  };

  const getRecommendationColor = (type: string) => {
    if (type === "critical") return "border-rose-500/20 bg-rose-500/10";
    if (type === "warning") return "border-amber-500/20 bg-amber-500/10";
    if (type === "success") return "border-emerald-500/20 bg-emerald-500/10";
    return "border-blue-500/20 bg-blue-500/10";
  };

  // Prepare chart data
  const chartData = performanceData.map((d) => ({
    date: new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    views: d.total_views,
    likes: d.total_likes,
    comments: d.total_comments,
    avgViews: d.avg_views
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Creator Analytics</h2>
          <p className="text-sm text-muted-foreground">Track your performance and growth</p>
        </div>
        <Button variant="outline" size="sm">
          <Clock className="h-4 w-4 mr-2" />
          Last 30 Days
        </Button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Views</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.total_views.toLocaleString()}</div>
            <div className="flex items-center mt-1 text-xs text-muted-foreground">
              <Video className="h-3 w-3 mr-1" />
              {metrics.total_reels_analyzed} reels
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Avg Engagement</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.avg_engagement_rate.toFixed(2)}%</div>
            <div className="flex items-center mt-1 text-xs text-muted-foreground">
              <Heart className="h-3 w-3 mr-1" />
              {metrics.total_likes.toLocaleString()} likes
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Growth Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {getGrowthIcon(metrics.growth_trend)}
              <span className={`text-2xl font-bold capitalize ${getGrowthColor(metrics.growth_trend)}`}>
                {metrics.growth_trend}
              </span>
            </div>
            <div className="flex items-center mt-1 text-xs text-muted-foreground">
              <TrendingUp className="h-3 w-3 mr-1" />
              Avg velocity: {metrics.avg_velocity_score.toFixed(1)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Viral Content</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.viral_content_count}</div>
            <div className="flex items-center mt-1 text-xs text-muted-foreground">
              <Award className="h-3 w-3 mr-1" />
              High-velocity pieces
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Performance Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Over Time</CardTitle>
          <CardDescription>Your content performance in the last 30 days</CardDescription>
        </CardHeader>
        <CardContent>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="date" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="views" stroke="#8b5cf6" strokeWidth={2} name="Views" />
                <Line type="monotone" dataKey="likes" stroke="#ec4899" strokeWidth={2} name="Likes" />
                <Line type="monotone" dataKey="comments" stroke="#14b8a6" strokeWidth={2} name="Comments" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-12">Not enough data yet</p>
          )}
        </CardContent>
      </Card>

      {/* Peak Hours & Optimal Times */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Peak Performance Hours</CardTitle>
            <CardDescription>When your content performs best</CardDescription>
          </CardHeader>
          <CardContent>
            {metrics.peak_performance_hours.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {metrics.peak_performance_hours.map((hour: number) => (
                  <Badge key={hour} variant="secondary">
                    {hour}:00 IST
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Not enough data yet</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Optimal Posting Times</CardTitle>
            <CardDescription>Recommended times to post</CardDescription>
          </CardHeader>
          <CardContent>
            {metrics.optimal_posting_times.length > 0 ? (
              <div className="space-y-2">
                {metrics.optimal_posting_times.map((time: string, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    {time}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Not enough data yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Content Categories */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Content by Category</CardTitle>
          <CardDescription>Your most successful content types</CardDescription>
        </CardHeader>
        <CardContent>
          {Object.keys(metrics.content_categories).length > 0 ? (
            <Suspense fallback={<div className="h-[200px] bg-muted rounded animate-pulse" />}>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={Object.entries(metrics.content_categories).map(([name, count]) => ({ name, count }))}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="name" className="text-xs" />
                  <YAxis className="text-xs" />
                  <Tooltip />
                  <Bar dataKey="count" fill="#8b5cf6" />
                </BarChart>
              </ResponsiveContainer>
            </Suspense>
          ) : (
            <p className="text-sm text-muted-foreground">Not enough data yet</p>
          )}
        </CardContent>
      </Card>

      {/* Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Personalized Recommendations</CardTitle>
          <CardDescription>Actionable insights to improve your performance</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {recommendations.map((rec, i) => (
              <div key={i} className={`p-4 rounded-lg border ${getRecommendationColor(rec.type)}`}>
                <div className="flex items-start gap-3">
                  {getRecommendationIcon(rec.type)}
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold mb-1">{rec.title}</h4>
                    <p className="text-xs text-muted-foreground mb-2">{rec.description}</p>
                    <p className="text-xs font-medium">{rec.action}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}