/**
 * Sample data for dashboard development.
 * Replace with actual data loaded from CSV/JSON when available.
 */

const SAMPLE_DATA = {
    // Summary metrics
    summary: {
        totalPlayers: 500,
        avgCareerYears: 2.4,
        medianCareerYears: 1.9,
        tier1Rate: 40.2,
        activeRate: 30.0,
        promotionRate: 24.8
    },

    // Regional distribution
    regions: {
        labels: ['LPL', 'LCK', 'LEC', 'LCS', 'VCS', 'PCS', 'CBLOL', 'LJL', 'LLA'],
        counts: [125, 100, 75, 60, 40, 35, 30, 20, 15],
        colors: ['#C8102E', '#E31937', '#0A74DA', '#003366', '#DA251D', '#00A651', '#009C3B', '#BC002D', '#006847']
    },

    // Career length data
    careerLength: {
        // Histogram bins
        histogram: {
            bins: [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 7, 8, 9, 10],
            counts: [45, 78, 85, 72, 58, 42, 35, 28, 22, 15, 10, 5, 3, 1, 1, 0]
        },
        // By region
        byRegion: {
            LCK: { mean: 2.8, median: 2.4, std: 1.5, count: 100 },
            LPL: { mean: 2.6, median: 2.2, std: 1.4, count: 125 },
            LEC: { mean: 2.4, median: 2.0, std: 1.3, count: 75 },
            LCS: { mean: 2.2, median: 1.8, std: 1.2, count: 60 },
            PCS: { mean: 2.0, median: 1.6, std: 1.1, count: 35 },
            VCS: { mean: 1.8, median: 1.5, std: 1.0, count: 40 },
            CBLOL: { mean: 1.6, median: 1.3, std: 0.9, count: 30 },
            LJL: { mean: 1.5, median: 1.2, std: 0.8, count: 20 },
            LLA: { mean: 1.4, median: 1.1, std: 0.8, count: 15 }
        },
        // By role
        byRole: {
            Top: { mean: 2.5, median: 2.1, std: 1.4, count: 100 },
            Jungle: { mean: 2.3, median: 1.9, std: 1.3, count: 100 },
            Mid: { mean: 2.6, median: 2.2, std: 1.5, count: 100 },
            ADC: { mean: 2.2, median: 1.8, std: 1.2, count: 100 },
            Support: { mean: 2.4, median: 2.0, std: 1.3, count: 100 }
        }
    },

    // Tier transition data
    tierTransitions: {
        tier2Starters: 325,
        promoted: 81,
        promotionRate: 24.9,
        avgTimeToPromotion: 14.2,
        // Time to promotion histogram
        timeHistogram: {
            bins: [3, 6, 9, 12, 15, 18, 21, 24, 30, 36],
            counts: [8, 15, 18, 14, 10, 7, 4, 3, 1, 1]
        },
        // By region
        byRegion: {
            LCK: { tier2: 60, promoted: 22, rate: 36.7 },
            LPL: { tier2: 75, promoted: 26, rate: 34.7 },
            LEC: { tier2: 50, promoted: 14, rate: 28.0 },
            LCS: { tier2: 40, promoted: 9, rate: 22.5 },
            VCS: { tier2: 30, promoted: 5, rate: 16.7 },
            PCS: { tier2: 25, promoted: 3, rate: 12.0 },
            CBLOL: { tier2: 22, promoted: 1, rate: 4.5 },
            LJL: { tier2: 13, promoted: 1, rate: 7.7 },
            LLA: { tier2: 10, promoted: 0, rate: 0.0 }
        }
    },

    // Regional comparison data
    regionalComparison: {
        eastern: {
            regions: ['LCK', 'LPL', 'PCS', 'VCS', 'LJL'],
            meanCareer: 2.34,
            medianCareer: 1.98
        },
        western: {
            regions: ['LEC', 'LCS', 'CBLOL', 'LLA'],
            meanCareer: 1.96,
            medianCareer: 1.55
        },
        // Box plot data (min, q1, median, q3, max)
        boxPlotData: {
            LCK: [0.5, 1.5, 2.4, 3.8, 8.2],
            LPL: [0.4, 1.4, 2.2, 3.5, 7.8],
            LEC: [0.3, 1.2, 2.0, 3.2, 6.5],
            LCS: [0.3, 1.0, 1.8, 2.8, 5.8],
            PCS: [0.3, 0.9, 1.6, 2.5, 5.0],
            VCS: [0.3, 0.8, 1.5, 2.3, 4.5],
            CBLOL: [0.2, 0.7, 1.3, 2.0, 4.0],
            LJL: [0.2, 0.6, 1.2, 1.8, 3.5],
            LLA: [0.2, 0.5, 1.1, 1.7, 3.2]
        }
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SAMPLE_DATA;
}
