//! Defines the [Signature] of a runtime as the mapping from tree-structured
//! [FunctionName]s to polymorphically-typed [FunctionDeclaration]s each available at
//! different [Location]s.
use crate::graph::TypeScheme;
use crate::symbol::{FunctionName, Label, Location, LocationName, Name, Prefix};
use itertools::join;
use std::collections::hash_map::Entry;
use std::collections::{HashMap, HashSet};
use thiserror::Error;

/// Information about a function: its polymorphic [TypeScheme], user-readable
/// description, and port ordering (for debug/display purposes, not used by
/// the typechecker).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FunctionDeclaration {
    /// Polymorphic type scheme describing all possible input/output types
    pub type_scheme: TypeScheme,
    /// User-readable documentation
    pub description: String,
    /// Order in which to display input ports
    pub input_order: Vec<Label>,
    /// Order in which to display output ports
    pub output_order: Vec<Label>,
}

/// Tree-structured mapping (sharing common prefixes) from [FunctionName]s
/// (to some kind of values, typically [FunctionDeclaration] or [NamespaceItem]).
#[derive(Debug, Clone)]
pub struct Namespace<T> {
    /// Items at this level of the name hierarchy
    pub functions: HashMap<Name, T>,
    /// Mappings for subtrees of the name hierarchy
    pub subspaces: HashMap<Prefix, Namespace<T>>,
}

/// Error when trying to merge two namespaces with different values for the same
/// [FunctionName].
#[derive(Debug, Error, Clone)]
#[error("Conflicting declarations for {}, in namespace {}", .0.name, join(.0.prefixes.iter(), "::"))]
pub struct ConflictingDeclaration(FunctionName);

impl ConflictingDeclaration {
    pub(crate) fn extend(mut self, ns: Prefix) -> Self {
        self.0.prefixes.insert(0, ns);
        self
    }
}

impl<T> Namespace<T> {
    /// Creates a new, empty, instance.
    pub fn new() -> Self {
        Namespace {
            functions: HashMap::new(),
            subspaces: HashMap::new(),
        }
    }

    /// `true` if there are no functions in the namespace, including in any
    /// [subspace](Namespace::subspaces); otherwise `false`.
    pub fn is_empty(&self) -> bool {
        self.functions.is_empty() && self.subspaces.values().all(|x| x.is_empty())
    }

    /// Consumes and transforms the namespace by applying a function to every value.
    /// (Keys are preserved.)
    pub fn map<S, F>(self, f: F) -> Namespace<S>
    where
        F: (Fn(T) -> S) + Clone,
    {
        let functions = self.functions.into_iter().map(|(k, v)| (k, f(v))).collect();

        let subspaces = self
            .subspaces
            .into_iter()
            .map(|(k, v)| (k, v.map(f.clone())))
            .collect();

        Namespace {
            functions,
            subspaces,
        }
    }

    /// Applies a function to the values in the namespace (keeping the same keys).
    /// The function takes the values by reference and the [Namespace] is not consumed.
    pub fn map_ref<S, F>(&self, f: F) -> Namespace<S>
    where
        F: (Fn(&T) -> S) + Clone,
    {
        let functions = self.functions.iter().map(|(k, v)| (*k, f(v))).collect();

        let subspaces = self
            .subspaces
            .iter()
            .map(|(k, v)| (*k, v.map_ref(f.clone())))
            .collect();

        Namespace {
            functions,
            subspaces,
        }
    }

    /// Merge a namespace into another namespace.
    ///
    /// `merge_funcs` combines two values (which had the same name), returning either
    /// `Some` of a new RHS value, or `None` to cause `merge_namespace` to return a
    /// [ConflictingDeclaration] error.
    pub fn merge_namespace<F>(
        &mut self,
        other: Namespace<T>,
        merge_funcs: F,
    ) -> Result<(), ConflictingDeclaration>
    where
        F: (Fn(T, T) -> Option<T>) + Clone,
    {
        for (name, func) in other.functions {
            match self.functions.entry(name) {
                Entry::Occupied(x) => {
                    match merge_funcs(x.remove(), func) {
                        Some(y) => self.functions.insert(name, y),
                        None => {
                            return Err(ConflictingDeclaration(FunctionName {
                                name,
                                prefixes: vec![],
                            }))
                        }
                    };
                }
                Entry::Vacant(x) => {
                    x.insert(func);
                }
            }
        }

        for (name, ns) in other.subspaces {
            match self.subspaces.entry(name) {
                Entry::Occupied(mut x) => {
                    x.get_mut()
                        .merge_namespace(ns, merge_funcs.clone())
                        .map_err(|e| e.extend(name))?;
                }
                Entry::Vacant(x) => {
                    x.insert(ns);
                }
            }
        }
        Ok(())
    }

    /// Recursively insert a function into a namespace
    pub fn insert_into_namespace(&mut self, name: FunctionName, item: T) {
        let mut ns = self;
        for space in name.prefixes.iter() {
            ns = ns.subspaces.entry(*space).or_default();
        }
        ns.functions.insert(name.name, item);
    }

    /// Gets an iterator over the RHS of all mappings, i.e. without any [FunctionName]s
    pub fn values(&self) -> Box<dyn Iterator<Item = &T> + '_> {
        let subs = self.subspaces.values().flat_map(|ss| ss.values());
        Box::new(self.functions.values().chain(subs))
    }

    /// Looks up a [FunctionName] starting at this point in the name hierarchy
    pub fn get(&self, name: &FunctionName) -> Option<&T> {
        let mut namespace = self;
        for ns in name.prefixes.iter() {
            namespace = namespace.subspaces.get(ns)?;
        }
        namespace.functions.get(&name.name)
    }

    /// Returns `true` if the namespace is a subset of another namespace `other`
    pub fn is_subset(&self, other: &Namespace<T>) -> bool
    where
        T: PartialEq,
    {
        self.functions
            .iter()
            .all(|(k, v)| other.functions.get(k) == Some(v))
            && self
                .subspaces
                .iter()
                .all(|(k, v)| match other.subspaces.get(k) {
                    None => false,
                    Some(v2) => v.is_subset(v2),
                })
    }
}

impl<T> Default for Namespace<T> {
    fn default() -> Self {
        Self::new()
    }
}

/// A [FunctionDeclaration] with a set of [Location]s at which
/// the function is supported.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NamespaceItem {
    /// Declaration of the function, including typescheme; identical at all locations
    pub decl: FunctionDeclaration,
    /// The locations (aka scopes) at which the function is supported
    pub locations: Vec<Location>,
}

/// The signature of a runtime is the functions and locations which it knows about.
#[derive(Debug, Clone, Default)]
pub struct Signature {
    /// Every function and location the runtime can run
    pub root: Namespace<NamespaceItem>,
    /// Named aliases for polymorphic types.
    pub aliases: HashMap<String, TypeScheme>,
    /// All the locations the runtime knows about.
    /// Must be disjoint from those of any other signature with which
    /// this one is [merged](Signature::merge_signature).
    pub scopes: HashSet<Location>,
}

/// Errors when trying to merge two Signatures - see [Signature::merge_signature]
#[derive(Error, Debug)]
pub enum SignatureError {
    /// The two signatures had different declarations for the same [FunctionName]
    #[error(transparent)]
    ConflictingDecl(#[from] ConflictingDeclaration),
    /// Both [Signature]s had the same [Location] in their [scopes](Signature::scopes)
    #[error("Scope at location {0} defined twice")]
    ScopeClash(Location),
}

impl Signature {
    /// Transforms this instance by nesting everything inside a [LocationName].
    /// For example, calling `in_location(loc)` on a [Signature] which declares
    /// a function "x" in a location "foo", returns a Signature declaring x in "loc::foo".
    pub fn in_location(mut self, loc: LocationName) -> Self {
        self.root = self.root.map(|x| NamespaceItem {
            decl: x.decl,
            locations: x.locations.into_iter().map(|x| x.prepend(loc)).collect(),
        });
        self.scopes = self.scopes.into_iter().map(|x| x.prepend(loc)).collect();
        self
    }

    /// Merges another signature into this, producing a new signature whose
    /// [scopes](Signature::scopes) and whose set of `(FunctionName, Location)` pairs
    /// are the union of the two input signatures.
    // ALAN this could be "disjoint union" if we knew a Signature's NamespaceItems were only supported in its own scopes.
    ///
    /// # Errors
    ///
    /// * If the two sets of [scopes](Signature::scopes) are not disjoint;
    /// * If the same function(name) is declared by both [Signature]s but with different [FunctionDeclaration]s.
    pub fn merge_signature(&mut self, other: Signature) -> Result<(), SignatureError> {
        self.root.merge_namespace(other.root, |a, b| {
            if a.decl != b.decl {
                None
            } else {
                let mut locations = a.locations;
                locations.extend(b.locations.into_iter());
                Some(NamespaceItem {
                    decl: a.decl,
                    locations,
                })
            }
        })?;

        for x in other.scopes {
            if !self.scopes.insert(x.clone()) {
                return Err(SignatureError::ScopeClash(x));
            }
        }

        for (name, type_) in other.aliases {
            if self.aliases.contains_key(&name) {
                continue;
            }

            self.aliases.insert(name, type_);
        }

        Ok(())
    }

    /// Returns `true` if the signature is a subset of another signature `other`
    pub fn is_subset(&self, other: &Signature) -> bool {
        self.root.is_subset(&other.root) && self.scopes.is_subset(&other.scopes)
    }

    /// Gets names and typeschemes (only) of all the functions declared
    /// in this signature. (That is, throws away all [Location] information,
    /// as well as fields of [FunctionDeclaration] other than
    /// [FunctionDeclaration::type_scheme].)
    pub fn type_schemes(self) -> Namespace<TypeScheme> {
        self.root.map(|x| x.decl.type_scheme)
    }
}
