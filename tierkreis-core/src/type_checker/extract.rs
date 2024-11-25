use super::solve::Solution;

/// Function that creates a `T` given access to a solved typing problem.
///
/// When type checking a graph or value we need to traverse the entire structure to collect all
/// constraints (including unifications and `Constraint`s). These constraints need to be completely
/// solved before we have access to the final types, so we can not construct a structure with the
/// type annotations in place immediately. Instead a `Extract<T>` can be returned that contains the
/// instructions on how to build `T` with type annotations once all the types are known.
pub(super) struct Extract<T>(Box<dyn FnOnce(&Solution) -> T>);

impl<T> Extract<T> {
    pub fn new<F>(f: F) -> Self
    where
        F: FnOnce(&Solution) -> T + 'static,
    {
        Extract(Box::new(f))
    }

    pub fn new_const(value: T) -> Self
    where
        T: 'static,
    {
        Extract(Box::new(move |_| value))
    }

    pub fn extract(self, solution: &Solution) -> T {
        (self.0)(solution)
    }
}
