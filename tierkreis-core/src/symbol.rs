//! Distinctly-typed names for elements of a graph
use crate::prelude::{TryFrom, TryInto};
use lasso::{Spur, ThreadedRodeo};
use once_cell::sync::Lazy;
use regex::Regex;
use std::borrow::Cow;
use std::convert::Infallible;
use std::ops::Deref;
use std::str::FromStr;
use thiserror::Error;
use uuid::Uuid;

static IDENT_REGEX: Lazy<Regex> = Lazy::new(|| Regex::new(r"^[\w--\d]\w*$").unwrap());

static SYMBOL_TABLE: Lazy<ThreadedRodeo> = Lazy::new(ThreadedRodeo::new);

fn intern<T>(value: T) -> Spur
where
    T: Into<Cow<'static, str>>,
{
    let value: Cow<'static, str> = value.into();
    match value {
        Cow::Borrowed(value) => SYMBOL_TABLE.get_or_intern_static(value),
        Cow::Owned(value) => SYMBOL_TABLE.get_or_intern(value),
    }
}

fn get(symbol: Spur) -> &'static str {
    SYMBOL_TABLE.resolve(&symbol)
}

/// Error with a potential qualified name.
#[derive(Error, Debug, Clone)]
pub enum SymbolError {
    /// Something that should be a qualified name isn't.
    #[error("Identifier name '{0}' is ill formed. Identifiers should contain word characters with the first character not being a number.")]
    IllFormedIdentifier(String),
}

impl From<Infallible> for SymbolError {
    fn from(infallible: Infallible) -> Self {
        match infallible {}
    }
}

macro_rules! make_symbol {
    {
        $(#[$meta:meta])*
        $vis:vis struct $struct_name:ident;
    }
    =>
    {
        $(#[$meta])*
        #[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
        $vis struct $struct_name(::lasso::Spur);

	impl $struct_name {
	    #[allow(dead_code)]
	    pub(crate) fn symbol<T>(v: T) -> Self
	    where
		T: TryInto<$struct_name>,
		<T as TryInto<$struct_name>>::Error: std::fmt::Debug,
	    {
		TryInto::try_into(v).unwrap()
	    }
	}

	impl<T> TryFrom<T> for $struct_name
	where
	    T: Into<Cow<'static, str>>
        {
	    type Error = SymbolError;

	    fn try_from(value: T) -> Result<Self, Self::Error> {
		let value = value.into();
		if IDENT_REGEX.is_match(value.deref()) {
		    Ok(Self(crate::symbol::intern(value)))
		} else {
		    Err(SymbolError::IllFormedIdentifier(value.to_string()))
		}
	    }
        }

	impl ::std::convert::AsRef<str> for $struct_name {
            fn as_ref(&self) -> &str {
                crate::symbol::get(self.0)
            }
        }

        impl ::std::fmt::Debug for $struct_name {
            fn fmt(&self, f: &mut ::std::fmt::Formatter<'_>) -> ::std::fmt::Result {
                f.write_str(crate::symbol::get(self.0))
            }
        }

        impl ::std::fmt::Display for $struct_name {
            fn fmt(&self, f: &mut ::std::fmt::Formatter<'_>) -> ::std::fmt::Result {
                f.write_str(crate::symbol::get(self.0))
            }
        }

	impl FromStr for $struct_name {
	    type Err = SymbolError;

	    fn from_str(s: &str) -> Result<Self, Self::Err> {
		TryInto::try_into(s.to_string())
	    }
	}
    }
}

make_symbol! {
    /// A namespace name
    pub struct Prefix;
}

make_symbol! {
    /// Name of a function
    pub struct Name;
}

/// Qualified name of a function.
#[derive(Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct FunctionName {
    /// Identifies a [Namespace] or subtree by traversing downward e.g. from the [root]
    ///
    /// [root]: crate::namespace::Signature::root
    /// [Namespace]: crate::namespace::Namespace
    pub prefixes: Vec<Prefix>,
    /// Name in that subspace
    pub name: Name,
}

impl std::fmt::Debug for FunctionName {
    fn fmt(&self, f: &mut ::std::fmt::Formatter<'_>) -> ::std::fmt::Result {
        for x in &self.prefixes {
            std::fmt::Debug::fmt(x, f)?;
            f.write_str("::")?;
        }
        std::fmt::Debug::fmt(&self.name, f)
    }
}

impl std::fmt::Display for FunctionName {
    fn fmt(&self, f: &mut ::std::fmt::Formatter<'_>) -> ::std::fmt::Result {
        for x in &self.prefixes {
            std::fmt::Display::fmt(x, f)?;
            f.write_str("::")?;
        }
        std::fmt::Display::fmt(&self.name, f)
    }
}

impl FromStr for FunctionName {
    type Err = SymbolError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let mut split: Vec<_> = s.split("::").collect();

        let name: Name = TryInto::try_into(split.pop().unwrap().to_string())?;
        let prefixes = split
            .into_iter()
            .map(|x| TryInto::try_into(x.to_string()))
            .collect::<Result<Vec<Prefix>, _>>()?;
        Ok(FunctionName { prefixes, name })
    }
}

impl FunctionName {
    /// `true` if the name has no prefixes, by convention indicating
    /// functions built-in to the Runtime.
    pub fn is_builtin(&self) -> bool {
        self.prefixes.is_empty()
    }

    /// Name of the `"discard"` builtin i.e. that takes a single input
    /// of any type and produces no output
    pub fn discard() -> Self {
        "discard".parse().unwrap()
    }

    /// A [Name] atom with no prefix, i.e. at the root of a [Namespace]
    ///
    /// [Namespace]: crate::namespace::Namespace
    pub fn builtin(name: Name) -> Self {
        FunctionName {
            prefixes: vec![],
            name,
        }
    }
}

make_symbol! {
    /// Label of a node port or entry in a row.
    pub struct Label;
}

impl Label {
    /// `"thunk"`, e.g. for the Graph input to an `eval` operation
    pub fn thunk() -> Self {
        Label::symbol("thunk")
    }

    /// `"value"`, used for many operations with a single output
    pub fn value() -> Self {
        Label::symbol("value")
    }

    /// The variant input to a `match` operation, which selects the handler
    pub fn variant_value() -> Self {
        Label::symbol("variant_value")
    }

    /// The `"break"` tag used by the body of a `loop` operation to end iteration.
    pub fn break_() -> Self {
        Label::symbol("break")
    }

    /// The `"continue"` tag used by the body of a `loop` operation to iterate again.
    pub fn continue_() -> Self {
        Label::symbol("continue")
    }
}

make_symbol! {
    /// Name of a type variable.
    pub struct TypeVar;
}

make_symbol! {
    /// Identifies at most one child of any given runtime;
    /// one atom in the structured name of a [Location]
    pub struct LocationName;
}

impl LocationName {
    /// Creates a [LocationName] from a UUID. The same for the same UUID,
    /// different from any `LocationName` built from a different UUID.
    pub fn from_uuid(uuid: Uuid) -> Self {
        LocationName::symbol(format!("_{}", uuid.simple()))
    }
}

/// Structured name identifying a path from a root to a Runtime
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Location(pub Vec<LocationName>);

impl Location {
    /// The zero-length path from a Runtime to itself
    pub fn local() -> Self {
        Location(vec![])
    }

    /// Prepends a single atom onto self (destructive update), i.e.
    /// `self` *after* `location`
    pub fn prepend(mut self, location: LocationName) -> Self {
        self.0.insert(0, location);
        self
    }

    /// Concatenates two structured names
    pub fn concat(mut self, location: &Location) -> Self {
        self.0.extend(location.0.iter());
        Location(self.0)
    }

    /// Gets the first atom (and the rest), if `self` is non-empty (aka `uncons`)
    pub fn pop(self) -> Option<(LocationName, Location)> {
        let mut iter = self.0.into_iter();
        iter.next().map(|name| (name, Location(iter.collect())))
    }
}

impl std::fmt::Display for Location {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let mut x = self.0.iter();
        if let Some(name) = x.next() {
            write!(f, "{}", name)?;

            for name in x {
                write!(f, "/{}", name)?;
            }
            Ok(())
        } else {
            f.write_str("<Local>")
        }
    }
}

impl FromStr for Location {
    type Err = SymbolError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let split = s.split('/');
        let names: Result<Vec<LocationName>, _> =
            split.map(|x| TryInto::try_into(x.to_string())).collect();
        Ok(Location(names?))
    }
}

#[cfg(test)]
mod tests {
    use std::error::Error;

    use super::{FunctionName, Label, TryFrom};
    use crate::symbol::Location;

    #[test]
    fn test_predefined_symbols() -> Result<(), Box<dyn Error>> {
        FunctionName::discard();
        Label::thunk();
        Label::value();
        Label::variant_value();
        Label::break_();
        Label::continue_();
        Ok(())
    }

    #[test]
    fn test_symbols() -> Result<(), Box<dyn Error>> {
        <Label as TryFrom<_>>::try_from("string")?;
        <Label as TryFrom<_>>::try_from("_underscore")?;
        <Label as TryFrom<_>>::try_from("hasnumbers123")?;
        <Label as TryFrom<_>>::try_from("unicodeαunicode")?;
        <Label as TryFrom<_>>::try_from("αunicode")?;
        <Label as TryFrom<_>>::try_from("middle_underscore")?;
        Ok(())
    }

    #[test]
    fn test_disallowed_symbols() -> Result<(), Box<dyn Error>> {
        assert!(<Label as TryFrom<_>>::try_from("").is_err());
        assert!(<Label as TryFrom<_>>::try_from("1startswithnumber").is_err());
        assert!(<Label as TryFrom<_>>::try_from("brackets()").is_err());
        assert!(<Label as TryFrom<_>>::try_from("has::colons").is_err());
        assert!(<Label as TryFrom<_>>::try_from("backslash\test").is_err());
        assert!(<Label as TryFrom<_>>::try_from("forwardslash/test").is_err());
        assert!(<Label as TryFrom<_>>::try_from("fullstop.test").is_err());
        assert!(<Label as TryFrom<_>>::try_from("s p a c e s").is_err());
        assert!(<Label as TryFrom<_>>::try_from("newline\n").is_err());
        assert!("<Local>".parse::<Location>().is_err());
        Ok(())
    }
}
