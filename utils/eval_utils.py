import torch
import torch.nn.functional as F

def top_filtering(logits, top_k=0., top_p=0.9, threshold=-float('Inf'), filter_value=-float('Inf')):
    """ Filter a distribution of logits using top-k, top-p (nucleus) and/or threshold filtering
        Args:
            logits: logits distribution shape (vocabulary size)
            top_k: <=0: no filtering, >0: keep only top k tokens with highest probability.
            top_p: <=0.0: no filtering, >0.0: keep only a subset S of candidates, where S is the smallest subset
                whose total probability mass is greater than or equal to the threshold top_p.
                In practice, we select the highest probability tokens whose cumulative probability mass exceeds
                the threshold top_p.
            threshold: a minimal threshold to keep logits
    """
    assert logits.dim() == 1  # Only work for batch size 1 for now - could update but it would obfuscate a bit the code
    top_k = min(top_k, logits.size(-1))
    if top_k > 0:
        # Remove all tokens with a probability less than the last token in the top-k tokens
        indices_to_remove = logits < torch.topk(logits, top_k)[0][..., -1, None]
        logits[indices_to_remove] = filter_value

    if top_p > 0.0:
        # Compute cumulative probabilities of sorted tokens
        sorted_logits, sorted_indices = torch.sort(logits, descending=True)
        cumulative_probabilities = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)

        # Remove tokens with cumulative probability above the threshold
        sorted_indices_to_remove = cumulative_probabilities > top_p
        # Shift the indices to the right to keep also the first token above the threshold
        sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
        sorted_indices_to_remove[..., 0] = 0

        # Back to unsorted indices and set them to -infinity
        indices_to_remove = sorted_indices[sorted_indices_to_remove]
        logits[indices_to_remove] = filter_value

    indices_to_remove = logits < threshold
    logits[indices_to_remove] = filter_value

    return logits


class ScoreTracker:
    def __init__(self, stop_after_epochs=5, initial_max=0):

        self.counter = 0
        self.max_score = initial_max
        self.stop_after_epochs = stop_after_epochs
        self.scores = []
        self.stop_training = False

    def __call__(self, score):
        
        if self.stop_after_epochs < 1:
            # deactivated -> always continue training
            return False
        
        self.max_score = max(self.scores) if len(self.scores) > 0 else self.max_score
        self.scores.append(score)
        
        if score <= self.max_score:
            self.counter += 1  # advance counter if max_score is not exceeded
        else: 
            self.counter = 0  # reset counter if max_score is exceeded

        if len(self.scores) >= self.stop_after_epochs:  
            #  after minimum number of epochs
            if self.counter >= self.stop_after_epochs:  
                # if max_score was not exceeded for threshold number of epochs
                self.stop_training = True
                
    def stop(self):
        return self.stop_training
    
    def print_summary(self, round_precision=3):
        last_score = round(self.scores[-1], round_precision)
        max_score = round(self.max_score, round_precision)
        score_diff = round(last_score - max_score, round_precision)
        
        print(f'last score: {last_score}')
        print(f'max score from previous epochs: {max_score}')
        if self.counter == 0:
            print('new max score achieved in this epoch')
        else: 
            print(f'max score achieved {self.counter} epochs ago')
        print(f'difference to previous max: {score_diff}')
        
        print(f'stop training: {self.stop_training}')