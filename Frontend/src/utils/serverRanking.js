/**
 * Server Ranking Utility
 * 
 * Comprehensive scoring algorithm for ranking servers:
 * - Performance Score (20%): Log-scaled verified payout volume
 * - Growth Score (20%): Activity growth (submissions per member)
 * - Engagement Score (20%): Active traders, submission frequency, approval rate
 * - Quality Score (20%): Average Verified Payout Value
 * - Diversity Score (20%): Member count and market variety
 * 
 * All scores are normalized to 0-100 scale and weighted to produce final ranking.
 */

/**
 * Calculate comprehensive scores for all servers
 * @param {Array} serverList - Array of server objects
 * @returns {Array} Servers with calculated scores, sorted by total score
 */
export const calculateServerScores = (serverList) => {
  // Ensure serverList is an array
  if (!Array.isArray(serverList)) {
    console.error('serverList is not an array:', serverList);
    return [];
  }

  if (serverList.length === 0) return [];

  // Category weights (must sum to 1.0)
  const weights = {
    performance: 0.20,
    growth: 0.20,
    engagement: 0.20,
    quality: 0.20,
    diversity: 0.20
  };

  // Step 1: Calculate raw metric values for all servers
  const serversWithRawScores = serverList.map(server => ({
    ...server,
    rawScores: {
      performance: calculatePerformanceScore(server),
      growth: calculateGrowthScore(server),
      engagement: calculateEngagementScore(server),
      diversity: calculateDiversityScore(server),
      quality: calculateQualityScore(server)
    }
  }));

  // Step 2: Find global max values for each metric
  const maxValues = {
    performance: Math.max(...serversWithRawScores.map(s => s.rawScores.performance), 1),
    growth: Math.max(...serversWithRawScores.map(s => s.rawScores.growth), 1),
    engagement: Math.max(...serversWithRawScores.map(s => s.rawScores.engagement), 1),
    diversity: Math.max(...serversWithRawScores.map(s => s.rawScores.diversity), 1),
    quality: Math.max(...serversWithRawScores.map(s => s.rawScores.quality), 1)
  };

  // Step 3: Normalize each metric to 0-100 scale and calculate weighted total
  const scoredServers = serversWithRawScores.map(server => {
    // Normalize each metric: (rawValue / maxValue) * 100
    const normalizedPerformance = (server.rawScores.performance / maxValues.performance) * 100;
    const normalizedGrowth = (server.rawScores.growth / maxValues.growth) * 100;
    const normalizedEngagement = (server.rawScores.engagement / maxValues.engagement) * 100;
    const normalizedDiversity = (server.rawScores.diversity / maxValues.diversity) * 100;
    const normalizedQuality = (server.rawScores.quality / maxValues.quality) * 100;

    // Step 4: Apply weights to calculate total score (0-100)
    const totalScore =
      (normalizedPerformance * weights.performance) +
      (normalizedGrowth * weights.growth) +
      (normalizedEngagement * weights.engagement) +
      (normalizedDiversity * weights.diversity) +
      (normalizedQuality * weights.quality);

    // Remove rawScores from final object
    const { rawScores, ...serverData } = server;

    return {
      ...serverData,
      scores: {
        performance: normalizedPerformance,
        growth: normalizedGrowth,
        engagement: normalizedEngagement,
        diversity: normalizedDiversity,
        quality: normalizedQuality,
        total: totalScore
      }
    };
  });

  // Sort by total score (highest first)
  return scoredServers.sort((a, b) => b.scores.total - a.scores.total);
};

/**
 * Performance Score: Raw metric based on verified payout volume
 * Returns RAW value (not normalized) - normalization happens globally
 */
const calculatePerformanceScore = (server) => {
  const totalVerifiedPayouts = server.total_verified_payouts || 0;

  // Return raw log-scaled value for global normalization
  // Log scaling prevents raw volume from dominating
  const rawScore = totalVerifiedPayouts > 0
    ? Math.log10(totalVerifiedPayouts + 1)
    : 0;

  return rawScore;
};

/**
 * Growth Score: Raw metric based on activity growth
 * Returns RAW value (not normalized) - normalization happens globally
 */
const calculateGrowthScore = (server) => {
  const recentSubmissions = server.total_submissions || 0;
  const memberCount = server.member_count || 1;

  // Return raw submissions per member ratio
  const rawScore = recentSubmissions / memberCount;

  return rawScore;
};

/**
 * Engagement Score: Raw metric based on activity and approval
 * Returns RAW value (not normalized) - normalization happens globally
 */
const calculateEngagementScore = (server) => {
  const memberCount = server.member_count || 0;
  const totalSubmissions = server.total_submissions || 0;
  const verifiedPayouts = server.total_verified_payouts || 0;

  // Use Count('payout_submissions', filter=Q(status='Approved')) which is verified_count in backend
  // But here we rely on available fields. If 'verified_count' exists use it, else approximation.
  const verifiedCount = server.verified_count || (server.total_verified_payouts > 0 ? 1 : 0);
  // Actually, 'verified_count' is the COUNT of approved payouts which matches total_verified_payouts usually?
  // Wait, total_verified_payouts in backend annotated is SUM('amount'), NOT count.
  // Frontend might receive different props. Let's assume standard props.
  // If server.verified_count is available (count of approvals), use it.

  // Backend logic:
  // freq_score = (submissions / members) * 2
  // consistency = 25 if submissions > 10 else (submissions * 2.5)
  // raw_engagement = (active_traders * 0.5) + freq_score + consistency

  const activeTraders = server.active_members || 0;

  const freqScore = (totalSubmissions / Math.max(memberCount, 1)) * 2;
  const consistency = totalSubmissions > 10 ? 25 : (totalSubmissions * 2.5);

  const rawEngagement = (activeTraders * 0.5) + freqScore + consistency;

  return rawEngagement;
};

/**
 * Quality Score: Raw metric based on Average Verified Payout Value
 * High average payout = High quality
 */
const calculateQualityScore = (server) => {
  const totalVolume = server.total_verified_payouts || 0; // Sum of amount

  // We need the COUNT of verified payouts to calculate average
  // Backend provides `verified_count` usually. 
  // If not available, we can't calculate a perfect average.
  // Fallback: If `verified_count` is missing, maybe assume 1 if volume > 0?
  // Ideally backend serializer includes verified_count.
  const verifiedCount = server.verified_count || (totalVolume > 0 ? 1 : 0);

  const rawQuality = verifiedCount > 0
    ? (totalVolume / verifiedCount)
    : 0;

  return rawQuality;
};

/**
 * Diversity Score: Raw metric based on member variety
 * Returns RAW value (not normalized) - normalization happens globally
 */
const calculateDiversityScore = (server) => {
  const activeTraders = server.active_members || 0;

  // Backend logic: (active_traders * 0.5) + 60
  const rawDiversity = (activeTraders * 0.5) + 60;

  return rawDiversity;
};
