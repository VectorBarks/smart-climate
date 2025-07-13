"""Test suite for weighted confidence calculation in LightweightOffsetLearner.

ABOUTME: Comprehensive tests for Issue #41 - accuracy-focused confidence calculation.
Tests weighted approach: accuracy 70%, sample count 20%, diversity 10%.
"""

import pytest
import math
from unittest.mock import Mock
from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner


class TestWeightedConfidenceCalculation:
    """Test weighted confidence calculation with accuracy focus."""

    @pytest.fixture
    def learner(self):
        """Create a LightweightOffsetLearner instance."""
        return LightweightOffsetLearner(max_history=100, learning_rate=0.1)

    def test_high_accuracy_gives_high_confidence(self, learner):
        """Test that high accuracy results in high confidence regardless of sample count."""
        # Add samples with perfect accuracy (predicted == actual)
        for i in range(10):
            learner.add_sample(
                predicted=2.0,
                actual=2.0,  # Perfect accuracy
                ac_temp=20.0,
                room_temp=22.0,
                mode="cool"
            )
        
        stats = learner.get_learning_stats()
        
        # With perfect accuracy, confidence should be high (>80%)
        assert stats.avg_accuracy > 0.8, f"Expected high confidence with perfect accuracy, got {stats.avg_accuracy}"

    def test_poor_accuracy_gives_low_confidence(self, learner):
        """Test that poor accuracy results in low confidence even with many samples."""
        # Add many samples with terrible accuracy
        for i in range(100):
            learner.add_sample(
                predicted=0.0,
                actual=3.0,  # MAE = 3.0, very poor accuracy
                ac_temp=20.0 + i * 0.1,
                room_temp=22.0 + i * 0.1,
                mode="cool"
            )
        
        stats = learner.get_learning_stats()
        
        # Even with 100 samples, poor accuracy should give low confidence (<30%)
        assert stats.avg_accuracy < 0.3, f"Expected low confidence with poor accuracy, got {stats.avg_accuracy}"

    def test_accuracy_penalty_doubling(self, learner):
        """Test that poor accuracy penalty is applied doubly."""
        # Add samples with poor accuracy (MAE = 2.0)
        for i in range(50):
            learner.add_sample(
                predicted=0.0,
                actual=2.0,  # MAE = 2.0
                ac_temp=20.0,
                room_temp=22.0,
                mode="cool"
            )
        
        stats = learner.get_learning_stats()
        
        # With MAE=2.0, prediction accuracy should be ~0.2
        # And should be heavily weighted in final confidence
        assert stats.avg_accuracy < 0.5, f"Expected poor confidence with MAE=2.0, got {stats.avg_accuracy}"

    def test_confidence_cap_at_80_percent_for_poor_accuracy(self, learner):
        """Test that confidence is capped at 80% when accuracy < 70%."""
        # Create scenario with moderate accuracy (~60%) but excellent other factors
        for i in range(200):  # Many samples for high sample confidence
            learner.add_sample(
                predicted=0.0,
                actual=1.0,  # MAE = 1.0, gives ~50% accuracy
                ac_temp=20.0 + i * 0.05,  # Good diversity
                room_temp=22.0 + i * 0.05,
                mode="cool",
                outdoor_temp=15.0 + i * 0.1,
                power=500 + i * 2
            )
            
            # Update pattern for time coverage
            learner.update_pattern(1.0, 15.0 + i * 0.1, i % 24, "cooling")
        
        stats = learner.get_learning_stats()
        
        # Even with excellent sample count, diversity and time coverage,
        # confidence should be capped due to poor accuracy
        assert stats.avg_accuracy <= 0.8, f"Expected confidence cap at 80%, got {stats.avg_accuracy}"

    def test_excellent_accuracy_allows_high_confidence(self, learner):
        """Test that excellent accuracy (>90%) allows confidence >90%."""
        # Add samples with excellent accuracy (MAE = 0.05)
        for i in range(50):
            learner.add_sample(
                predicted=2.0,
                actual=2.05,  # MAE = 0.05, excellent accuracy
                ac_temp=20.0 + i * 0.1,
                room_temp=22.0 + i * 0.1,
                mode="cool",
                outdoor_temp=15.0 + i * 0.1
            )
            
            # Update patterns for good coverage
            learner.update_pattern(2.05, 15.0 + i * 0.1, i % 24, "cooling")
        
        stats = learner.get_learning_stats()
        
        # With excellent accuracy, confidence should be very high (>80%)
        assert stats.avg_accuracy > 0.8, f"Expected very high confidence with excellent accuracy, got {stats.avg_accuracy}"

    def test_new_system_has_low_confidence(self, learner):
        """Test that a new system with no samples has low confidence."""
        stats = learner.get_learning_stats()
        
        # New system should have 0 confidence
        assert stats.avg_accuracy == 0.0, f"Expected 0 confidence for new system, got {stats.avg_accuracy}"

    def test_terrible_accuracy_gives_near_zero_confidence(self, learner):
        """Test that terrible accuracy (MAE > 3.0) gives near-zero confidence."""
        # Add samples with terrible accuracy
        for i in range(20):
            learner.add_sample(
                predicted=0.0,
                actual=4.0,  # MAE = 4.0, terrible accuracy
                ac_temp=20.0,
                room_temp=22.0,
                mode="cool"
            )
        
        stats = learner.get_learning_stats()
        
        # Terrible accuracy should give near-zero confidence
        assert stats.avg_accuracy < 0.1, f"Expected near-zero confidence with terrible accuracy, got {stats.avg_accuracy}"

    def test_confidence_calculation_is_accuracy_focused(self, learner):
        """Test that accuracy is weighted much more heavily than other factors."""
        # Create scenario where accuracy is poor but other factors are good
        samples_to_add = 100  # High sample count
        
        for i in range(samples_to_add):
            learner.add_sample(
                predicted=0.0,
                actual=1.5,  # MAE = 1.5, poor accuracy (~30%)
                ac_temp=20.0 + i * 0.1,  # Good diversity
                room_temp=22.0 + i * 0.1,
                mode="cool",
                outdoor_temp=15.0 + i * 0.2,
                power=500 + i * 5
            )
            
            # Update patterns for excellent time coverage
            learner.update_pattern(1.5, 15.0 + i * 0.2, i % 24, "cooling")
        
        stats = learner.get_learning_stats()
        
        # Despite excellent sample count, diversity, and time coverage,
        # poor accuracy should dominate and keep confidence low
        assert stats.avg_accuracy < 0.6, f"Expected accuracy to dominate confidence calculation, got {stats.avg_accuracy}"

    def test_backward_compatibility_with_existing_interface(self, learner):
        """Test that the confidence calculation maintains existing interface."""
        # Add some samples
        for i in range(10):
            learner.add_sample(
                predicted=1.0,
                actual=1.1,
                ac_temp=20.0,
                room_temp=22.0,
                mode="cool"
            )
        
        stats = learner.get_learning_stats()
        
        # Check that all expected fields are present
        assert hasattr(stats, 'avg_accuracy'), "avg_accuracy field missing"
        assert hasattr(stats, 'samples_collected'), "samples_collected field missing"
        assert hasattr(stats, 'patterns_learned'), "patterns_learned field missing"
        assert hasattr(stats, 'last_sample_time'), "last_sample_time field missing"
        
        # Check that avg_accuracy is in valid range
        assert 0.0 <= stats.avg_accuracy <= 1.0, f"avg_accuracy out of range: {stats.avg_accuracy}"

    def test_edge_case_single_perfect_sample(self, learner):
        """Test edge case with single perfect sample."""
        learner.add_sample(
            predicted=2.0,
            actual=2.0,  # Perfect accuracy
            ac_temp=20.0,
            room_temp=22.0,
            mode="cool"
        )
        
        stats = learner.get_learning_stats()
        
        # Single perfect sample should give reasonable confidence
        assert 0.3 <= stats.avg_accuracy <= 0.8, f"Expected moderate confidence for single perfect sample, got {stats.avg_accuracy}"

    def test_edge_case_mixed_accuracy_samples(self, learner):
        """Test with mixed accuracy samples."""
        # Add mix of perfect and poor samples
        for i in range(5):
            learner.add_sample(
                predicted=2.0,
                actual=2.0,  # Perfect accuracy
                ac_temp=20.0,
                room_temp=22.0,
                mode="cool"
            )
        
        for i in range(5):
            learner.add_sample(
                predicted=2.0,
                actual=3.0,  # Poor accuracy (MAE = 1.0)
                ac_temp=20.0,
                room_temp=22.0,
                mode="cool"
            )
        
        stats = learner.get_learning_stats()
        
        # Mixed accuracy should give moderate confidence
        assert 0.2 <= stats.avg_accuracy <= 0.8, f"Expected moderate confidence for mixed accuracy, got {stats.avg_accuracy}"

    def test_confidence_increases_with_better_accuracy(self, learner):
        """Test that confidence increases as accuracy improves."""
        confidences = []
        
        # Test different accuracy levels
        mae_levels = [3.0, 2.0, 1.0, 0.5, 0.1]  # Improving accuracy
        
        for mae in mae_levels:
            test_learner = LightweightOffsetLearner(max_history=100, learning_rate=0.1)
            
            # Add samples with specific MAE
            for i in range(30):
                test_learner.add_sample(
                    predicted=2.0,
                    actual=2.0 + mae,  # Control MAE
                    ac_temp=20.0 + i * 0.1,
                    room_temp=22.0 + i * 0.1,
                    mode="cool"
                )
            
            stats = test_learner.get_learning_stats()
            confidences.append(stats.avg_accuracy)
        
        # Confidence should generally increase as accuracy improves (MAE decreases)
        for i in range(1, len(confidences)):
            assert confidences[i] >= confidences[i-1], \
                f"Confidence should increase with better accuracy. Got {confidences}"

    def test_weighted_calculation_method_exists(self, learner):
        """Test that the weighted confidence calculation method can be called directly."""
        # Add some samples first
        for i in range(10):
            learner.add_sample(
                predicted=1.0,
                actual=1.1,
                ac_temp=20.0,
                room_temp=22.0,
                mode="cool"
            )
        
        # Test that we can call the internal methods used in weighted calculation
        sample_confidence = learner._calculate_sample_count_confidence()
        accuracy_factor = learner._calculate_prediction_accuracy()
        diversity_factor = learner._calculate_condition_diversity_confidence()
        
        # All should return valid confidence values
        assert 0.0 <= sample_confidence <= 1.0, f"Invalid sample confidence: {sample_confidence}"
        assert 0.0 <= accuracy_factor <= 1.0, f"Invalid accuracy factor: {accuracy_factor}"
        assert 0.0 <= diversity_factor <= 1.0, f"Invalid diversity factor: {diversity_factor}"

    def test_accuracy_weight_is_dominant(self, learner):
        """Test that accuracy factor has dominant weight in calculation."""
        # Create scenario to test internal weighting
        # We'll monkey-patch the internal methods to control their outputs
        
        # Mock high values for non-accuracy factors
        learner._calculate_sample_count_confidence = Mock(return_value=1.0)
        learner._calculate_condition_diversity_confidence = Mock(return_value=1.0) 
        learner._calculate_time_coverage_confidence = Mock(return_value=1.0)
        
        # Test with poor accuracy
        learner._calculate_prediction_accuracy = Mock(return_value=0.1)
        learner._sample_count = 100  # Trigger mature phase
        learner._enhanced_samples = [{"predicted": 0, "actual": 0}]  # Dummy sample
        
        stats = learner.get_learning_stats()
        
        # Even with perfect other factors, poor accuracy should dominate
        assert stats.avg_accuracy < 0.5, f"Expected poor accuracy to dominate, got {stats.avg_accuracy}"

    def test_confidence_never_exceeds_accuracy_when_poor(self, learner):
        """Test that confidence never exceeds accuracy when accuracy is poor."""
        # Add samples with known poor accuracy
        for i in range(50):
            learner.add_sample(
                predicted=0.0,
                actual=2.0,  # MAE = 2.0, should give ~20% accuracy
                ac_temp=20.0 + i,
                room_temp=22.0 + i,
                mode="cool",
                outdoor_temp=15.0 + i,
                power=500 + i * 10
            )
            
            # Add excellent pattern coverage
            learner.update_pattern(2.0, 15.0 + i, i % 24, "cooling")
        
        stats = learner.get_learning_stats()
        
        # Calculate what the accuracy factor should be (MAE = 2.0 -> ~0.2)
        expected_accuracy_factor = 0.2  # From _calculate_prediction_accuracy logic
        
        # Final confidence should be dominated by poor accuracy
        assert stats.avg_accuracy <= expected_accuracy_factor * 1.5, \
            f"Confidence {stats.avg_accuracy} should not exceed accuracy factor {expected_accuracy_factor} by much"