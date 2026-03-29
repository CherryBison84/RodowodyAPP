"""
Średni kinship (średnia współzgodności Φ Malecota / Wrighta) po parach osobników.

Dla dużych populacji pełne O(n²) jest niepraktyczne — stosujemy losową próbkę osobników
i średnią Φ po parach w próbie (przybliżenie; ten sam limit głębokości co przy F / Φ par).
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence, Tuple

from app.analytics.inbreeding_wright import wright_offspring_inbreeding_F_from_parents
from app.pedigree.ancestor_pedigree import Person


def mean_kinship_pairwise(
    people: Dict[str, Person],
    individual_ids: Sequence[str],
    *,
    max_generations_back: int | None,
    exhaustive_max_n: int = 50,
    random_sample_n: int = 72,
    random_seed: int = 42,
) -> Tuple[Optional[float], Optional[float], str]:
    """
    Średnia z Φ(i,j) po parach i≠j (kolejność bez znaczenia; Φ symetryczne).

    - Gdy n ≤ `exhaustive_max_n`: wszystkie n·(n−1)/2 par.
    - Gdy n większe: losowa próba `min(random_sample_n, n)` ID, potem wszystkie pary w próbie.

    Zwraca: (średnia_Φ, średnie_R=2Φ, krótki opis metody).
    """
    ids = [str(x) for x in individual_ids if str(x) in people]
    n = len(ids)
    if n < 2:
        return None, None, "Za mało osobników (min. 2 z rekordem w bazie)."

    used_ids: List[str]
    note_extra = ""
    if n <= exhaustive_max_n:
        used_ids = ids
    else:
        rng = random.Random(random_seed)
        k = min(random_sample_n, n)
        used_ids = rng.sample(ids, k)
        note_extra = (
            f"Próba losowa k={k} z n={n} (pełna enumeracja par przy n≤{exhaustive_max_n}). "
        )

    m = len(used_ids)
    total_phi = 0.0
    pair_count = 0
    for i in range(m):
        a = used_ids[i]
        for j in range(i + 1, m):
            b = used_ids[j]
            phi = wright_offspring_inbreeding_F_from_parents(
                a,
                b,
                people,
                max_generations_back=max_generations_back,
            )
            total_phi += float(phi)
            pair_count += 1

    if pair_count == 0:
        return None, None, "Brak par do uśrednienia."

    mean_phi = total_phi / float(pair_count)
    mean_r = 2.0 * mean_phi
    note = (
        note_extra
        + f"Średnia Φ po {pair_count} parach (i≠j); R̄ = 2Φ̄ (Wright, autosomy)."
    )
    return mean_phi, mean_r, note
