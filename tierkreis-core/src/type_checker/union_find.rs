use std::cell::Cell;

/// [Disjoint-set data structure] using Tarjan's union find algorithm with path compression and
/// union by size.
///
/// [Disjoint-set data structure]: https://en.wikipedia.org/wiki/Disjoint-set_data_structure
#[derive(Clone)]
pub(super) struct UnionFind {
    parents: Vec<Cell<usize>>,
    sizes: Vec<usize>,
}

impl std::fmt::Debug for UnionFind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("UnionFind").finish()
    }
}

impl UnionFind {
    pub fn new() -> Self {
        UnionFind {
            parents: Vec::new(),
            sizes: Vec::new(),
        }
    }

    pub fn make_set(&mut self) -> usize {
        let index = self.parents.len();
        self.parents.push(Cell::new(index));
        self.sizes.push(1);
        index
    }

    pub fn find(&self, mut index: usize) -> usize {
        while self.parents[index].get() != index {
            let parent = self.parents[index].get();
            self.parents[index].set(self.parents[parent].get());
            index = parent;
        }

        index
    }

    pub fn union(&mut self, a: usize, b: usize) -> Union {
        let a = self.find(a);
        let b = self.find(b);

        if a == b {
            return Union::Same;
        }

        let (root, inner) = if self.sizes[a] >= self.sizes[b] {
            (a, b)
        } else {
            (b, a)
        };

        self.parents[inner].set(root);
        self.sizes[root] += self.sizes[inner];
        Union::Merged(root, inner)
    }

    /// Iterator over those indices `i` for which `find(i) = i`.
    pub fn roots(&self) -> impl Iterator<Item = usize> + '_ {
        self.parents
            .iter()
            .enumerate()
            .filter(|(index, parent)| *index == parent.get())
            .map(|(index, _)| index)
    }
}

impl Default for UnionFind {
    fn default() -> Self {
        Self::new()
    }
}

pub enum Union {
    Same,
    Merged(usize, usize),
}
