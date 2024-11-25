//! We make our own TryFrom trait to avoid a blanket implementation causing conflicts
//! See <https://github.com/rust-lang/rust/issues/50133>
use std::convert::Infallible;

/// Like [std::convert::TryFrom] (but without the library blanket impls!)
pub trait TryFrom<T>: Sized {
    /// The type returned in the event of a conversion error.
    type Error;

    /// Performs the conversion.
    fn try_from(value: T) -> Result<Self, Self::Error>;
}

/// Like [std::convert::TryInto] (but without the library blanket impls!)
pub trait TryInto<T>: Sized {
    /// The type returned in the event of a conversion error.
    type Error;

    /// Performs the conversion.
    fn try_into(self) -> Result<T, Self::Error>;
}

impl<T, U> TryInto<U> for T
where
    U: TryFrom<T>,
{
    type Error = U::Error;

    fn try_into(self) -> Result<U, U::Error> {
        <U as TryFrom<_>>::try_from(self)
    }
}

impl<T> TryFrom<T> for T {
    type Error = Infallible;

    fn try_from(value: T) -> Result<Self, Self::Error> {
        Ok(value)
    }
}

impl TryFrom<i64> for u32 {
    type Error = <u32 as std::convert::TryFrom<i64>>::Error;

    fn try_from(value: i64) -> Result<Self, Self::Error> {
        std::convert::TryFrom::try_from(value)
    }
}
