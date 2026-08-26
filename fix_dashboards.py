import os

def fix_india_dashboard():
    with open('frontend/src/components/IndiaFeaturesDashboard.tsx', 'r', encoding='utf-8') as f:
        content = f.read()
        
    content = content.replace('import { getRegionalTrends', 'import { useUserStore } from "@/store/useAppStore";\nimport { getRegionalTrends')
    content = content.replace('const [loading, setLoading] = useState(false);', 'const [loading, setLoading] = useState(false);\n  const userPlan = useUserStore((s) => s.plan) || "free";')
    content = content.replace('setLoading(true);\n    try {\n      const [trends', 'setLoading(true);\n    if (userPlan === "free") {\n      setRegionalTrends(getFallbackTrends(selectedRegion));\n      setTiming(getFallbackTiming(selectedRegion));\n      setCulturalEvents(getFallbackEvents(selectedRegion));\n      setCreatorPatterns(getFallbackPatterns(selectedRegion));\n      setLoading(false);\n      return;\n    }\n    try {\n      const [trends')
    
    with open('frontend/src/components/IndiaFeaturesDashboard.tsx', 'w', encoding='utf-8') as f:
        f.write(content)

def fix_creator_analytics():
    with open('frontend/src/components/CreatorAnalyticsDashboard.tsx', 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'useUserStore' not in content:
        content = content.replace('import { getCreatorMetrics', 'import { useUserStore } from "@/store/useAppStore";\nimport { getCreatorMetrics')
        content = content.replace('const [loading, setLoading] = useState(true);', 'const [loading, setLoading] = useState(true);\n  const userPlan = useUserStore((s) => s.plan) || "free";')
        
    content = content.replace('setLoading(true);\n        const [metricsData', 'setLoading(true);\n        if (userPlan === "free") {\n          setLoading(false);\n          return;\n        }\n        const [metricsData')
    
    with open('frontend/src/components/CreatorAnalyticsDashboard.tsx', 'w', encoding='utf-8') as f:
        f.write(content)

def fix_early_detection():
    with open('frontend/src/components/EarlyDetectionPanel.tsx', 'r', encoding='utf-8') as f:
        content = f.read()
        
    content = content.replace('const fetchEarlyTrends = async () => {\n    try {\n      // Use apiFetch', 'const fetchEarlyTrends = async () => {\n    if (userPlan === "free") {\n      setEarlyTrends([]);\n      setLoading(false);\n      return;\n    }\n    try {\n      // Use apiFetch')
    
    with open('frontend/src/components/EarlyDetectionPanel.tsx', 'w', encoding='utf-8') as f:
        f.write(content)

fix_india_dashboard()
fix_creator_analytics()
fix_early_detection()
print("Fixed dashboards!")
