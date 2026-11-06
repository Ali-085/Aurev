/**
 * Subscription Tier Utilities
 * 
 * Handles tier checking and feature access control on frontend.
 * Mirrors backend tier system for consistent UX.
 */

/**
 * Tier levels for comparison
 */
const TIER_LEVELS = {
  'standard': 1,
  'premium': 2,
  'elite': 3,
};

/**
 * Get tier level number
 */
export const getTierLevel = (tier) => {
  return TIER_LEVELS[tier?.toLowerCase()] || 0;
};

/**
 * Check if user has required tier access
 */
export const hasTierAccess = (userTier, requiredTier) => {
  const userLevel = getTierLevel(userTier);
  const requiredLevel = getTierLevel(requiredTier);
  return userLevel >= requiredLevel;
};

/**
 * Get feature availability for a specific tier
 */
export const getTierFeatures = (tier) => {
  const normalizedTier = tier?.toLowerCase();
  
  if (normalizedTier === 'standard') {
    return {
      // Data Access
      totalVerifiedPayouts: true,
      totalPayoutVolume: true,
      uniqueTradersCount: true,
      sevenDayVolume: true,
      thirtyDayVolume: true,
      basicTimelineChart: true,
      submissionCountPerDay: true,
      basicHealthScore: true,
      topTradersTop5: true,
      
      // Advanced Data (Premium+)
      hourlyDistribution: false,
      traderCategorization: false,
      consistencyScores: false,
      marketTrendAnalysis: false,
      predictiveInsights: false,
      comparativeBenchmarks: false,
      topTradersTop10: false,
      momentumTimeline: false,
      healthComponentBreakdown: false,
      rankProgression: false,
      detailedBonusMetrics: false,
      
      // Elite Features

      advancedFraudDetection: false,
      apiAccess: false,
      prioritySupport: false,
      benchmarkAnalytics: false,
      historicalData: false,
      forecastProjections: false,
    };
  } else if (normalizedTier === 'premium') {
    return {
      // All Standard features
      totalVerifiedPayouts: true,
      totalPayoutVolume: true,
      uniqueTradersCount: true,
      sevenDayVolume: true,
      thirtyDayVolume: true,
      basicTimelineChart: true,
      submissionCountPerDay: true,
      basicHealthScore: true,
      topTradersTop5: true,
      topTradersTop10: true,
      
      // Premium features
      hourlyDistribution: true,
      traderCategorization: true,
      consistencyScores: true,
      marketTrendAnalysis: true,
      predictiveInsights: true,
      comparativeBenchmarks: false, // Elite only
      momentumTimeline: true,
      healthComponentBreakdown: true,
      rankProgression: true,
      detailedBonusMetrics: true,
      
      // Elite Features

      advancedFraudDetection: false,
      apiAccess: false,
      prioritySupport: false,
      benchmarkAnalytics: false,
      historicalData: false,
      forecastProjections: false,
    };
  } else if (normalizedTier === 'elite') {
    return {
      // All features unlocked
      totalVerifiedPayouts: true,
      totalPayoutVolume: true,
      uniqueTradersCount: true,
      sevenDayVolume: true,
      thirtyDayVolume: true,
      basicTimelineChart: true,
      submissionCountPerDay: true,
      basicHealthScore: true,
      topTradersTop5: true,
      topTradersTop10: true,
      hourlyDistribution: true,
      traderCategorization: true,
      consistencyScores: true,
      marketTrendAnalysis: true,
      predictiveInsights: true,
      comparativeBenchmarks: true,
      momentumTimeline: true,
      healthComponentBreakdown: true,
      rankProgression: true,
      detailedBonusMetrics: true,

      advancedFraudDetection: true,
      apiAccess: true,
      prioritySupport: true,
      benchmarkAnalytics: true,
      historicalData: true,
      forecastProjections: true,
    };
  }
  
  // Free tier (no subscription)
  return {
    totalVerifiedPayouts: false,
    totalPayoutVolume: false,
    uniqueTradersCount: false,
    sevenDayVolume: false,
    thirtyDayVolume: false,
    basicTimelineChart: false,
    submissionCountPerDay: false,
    basicHealthScore: false,
    topTradersTop5: false,
    topTradersTop10: false,
    hourlyDistribution: false,
    traderCategorization: false,
    consistencyScores: false,
    marketTrendAnalysis: false,
    predictiveInsights: false,
    comparativeBenchmarks: false,
    momentumTimeline: false,
    healthComponentBreakdown: false,
    rankProgression: false,
    detailedBonusMetrics: false,
    advancedFraudDetection: false,
    apiAccess: false,
    prioritySupport: false,
    benchmarkAnalytics: false,
    historicalData: false,
    forecastProjections: false,
  };
};

/**
 * Get tier display info
 */
export const getTierInfo = (tier) => {
  const normalizedTier = tier?.toLowerCase();
  
  const tierInfo = {
    'standard': {
      name: 'Standard',
      color: '#007bff',
      icon: '',
      price: '$19.99/mo',
      description: 'Essential analytics for growing servers'
    },
    'premium': {
      name: 'Premium',
      color: '#9C27B0',
      icon: '',
      price: '$49.99/mo',
      description: 'Advanced insights and trader intelligence'
    },
    'elite': {
      name: 'Elite',
      color: '#FFD700',
      icon: '',
      price: '$99.99/mo',
      description: 'Complete analytics suite with benchmarking'
    },
    'free': {
      name: 'Free',
      color: '#6c757d',
      icon: '',
      price: 'Free',
      description: 'Basic server management'
    }
  };
  
  return tierInfo[normalizedTier] || tierInfo['free'];
};

/**
 * Get suggested upgrade tier
 */
export const getSuggestedUpgrade = (currentTier) => {
  const normalizedTier = currentTier?.toLowerCase();
  
  if (!normalizedTier || normalizedTier === 'free') {
    return 'standard';
  } else if (normalizedTier === 'standard') {
    return 'premium';
  } else if (normalizedTier === 'premium') {
    return 'elite';
  }
  
  return null; // Already at max tier
};

/**
 * Format tier name for display
 */
export const formatTierName = (tier) => {
  if (!tier) return 'Free';
  return tier.charAt(0).toUpperCase() + tier.slice(1).toLowerCase();
};
